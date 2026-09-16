"""
API moteur pure, pour l'IA (feuille de route D1).

Le reste du projet joue une partie en écrivant un fichier JSON par round (`game_service`). Pour entraîner une IA
il faut l'inverse : des parties en mémoire, sans disque, et un état qu'on peut copier, mettre de côté, rejouer.

Trois fonctions suffisent, et c'est le vocabulaire standard de l'apprentissage par renforcement :

    new_game(...)            -> un état de départ
    legal_actions(state, side) -> les coups jouables par un camp
    step(state, ally, enemy) -> (nouvel état, ce qui s'est passé)

Règle d'or : **rien n'est modifié sur place**. `step` renvoie un nouvel état et laisse l'ancien intact, ce qui
permet à une IA d'essayer un coup « pour voir » sans casser la partie en cours.
"""
import copy
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from src.core.ai.opponent import Pick, legal_picks
from src.core.domain.card import Card
from src.core.domain.game import NB_ROUNDS, Game
from src.core.domain.player import Player
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import ProcessRoundInput

STARTING_LIFE = 12
STARTING_PILLZ = 12

SIDES = ("ally", "enemy")


@dataclass(frozen=True)
class StepResult:
    """Ce que le round vient de produire. `reward` est du point de vue de l'allié."""
    done: bool
    winner: Optional[str]          # "ally", "enemy", "draw", ou None si la partie continue
    life: Dict[str, int]
    reward: float                  # 0 tant que la partie continue ; à la fin : +1 victoire, -1 défaite, 0 nul
    life_gap: int                  # vie allié - vie ennemi (signal plus fin que la seule victoire)


def new_game(ally_cards: Sequence[Card], enemy_cards: Sequence[Card],
             life: int = STARTING_LIFE, pillz: int = STARTING_PILLZ) -> Game:
    """Un état de départ en mémoire (aucun fichier créé, contrairement à `game_service.create_game`)."""
    game = Game(1, True,
                Player(name="ally", life=life, pillz=pillz),
                Player(name="enemy", life=life, pillz=pillz),
                [])
    game.ally.cards = [copy.deepcopy(card) for card in ally_cards]
    game.enemy.cards = [copy.deepcopy(card) for card in enemy_cards]
    return game


def legal_actions(state: Game, side: str) -> List[Pick]:
    """Les coups jouables par `side` : carte non jouée x pillz misables x fury si payable."""
    if side not in SIDES:
        raise ValueError(f"Unknown side: {side!r}")
    if is_terminal(state):
        return []
    return legal_picks(state, side)


def is_terminal(state: Game) -> bool:
    """La partie est finie : 4 rounds joués, ou un joueur à 0 vie."""
    return state.nb_turn > NB_ROUNDS or state.ally.life <= 0 or state.enemy.life <= 0


def winner(state: Game) -> Optional[str]:
    """Qui a gagné, ou None si la partie continue. Égalité de vie en fin de 4 rounds = nul."""
    if not is_terminal(state):
        return None
    if state.ally.life <= 0 and state.enemy.life <= 0:
        return "draw"
    if state.enemy.life <= 0:
        return "ally"
    if state.ally.life <= 0:
        return "enemy"
    if state.ally.life > state.enemy.life:
        return "ally"
    if state.ally.life < state.enemy.life:
        return "enemy"
    return "draw"


def step(state: Game, ally_action: Pick, enemy_action: Pick) -> Tuple[Game, StepResult]:
    """
    Joue un round. Renvoie un **nouvel** état : `state` n'est pas touché.

    Les deux camps choisissent en même temps (c'est le cas dans Urban Rivals : on ne voit pas le coup adverse
    avant de jouer), d'où les deux actions d'un coup.
    """
    if is_terminal(state):
        raise ValueError("Game is already finished.")

    round_data = ProcessRoundInput(
        player1_card_index=ally_action.card_index, player1_pillz=ally_action.pillz, player1_fury=ally_action.fury,
        player2_card_index=enemy_action.card_index, player2_pillz=enemy_action.pillz, player2_fury=enemy_action.fury,
    )
    next_state = copy.deepcopy(state)
    check_round_correct(next_state, round_data)
    process_round(next_state, round_data)

    done = is_terminal(next_state)
    who = winner(next_state)
    return next_state, StepResult(
        done=done,
        winner=who,
        life={"ally": next_state.ally.life, "enemy": next_state.enemy.life},
        reward={"ally": 1.0, "enemy": -1.0, "draw": 0.0}.get(who, 0.0) if done else 0.0,
        life_gap=next_state.ally.life - next_state.enemy.life,
    )


def random_deck(catalogue: Sequence[dict], rng: random.Random, size: int = 4) -> List[Card]:
    """
    Tire `size` cartes au hasard dans le catalogue officiel, à leur niveau maximum.

    Construire une carte coûte cher (lecture des données officielles + parsing du pouvoir) : pour entraîner sur
    des milliers de parties, passer par `DeckPool` qui garde les cartes en cache.
    """
    picked = rng.sample(list(catalogue), size)
    return [Card(card_name=entry["name"], nb_stars=entry["levels"][-1]["stars"]) for entry in picked]


class DeckPool:
    """
    Réservoir de cartes prêtes à l'emploi.

    Sans cache, chaque partie repaie la construction des 8 cartes (~1,4 ms), soit plus que le temps de jeu
    lui-même. On construit donc chaque carte une fois, puis on en recopie l'exemplaire.
    """

    def __init__(self, catalogue: Sequence[dict], only_supported: bool = True):
        entries = list(catalogue)
        if only_supported:
            # Écarter les cartes dont le pouvoir n'est pas géré : l'IA apprendrait sur des règles fausses.
            entries = [entry for entry in entries
                       if entry.get("bonus_supported", True)
                       and all(level.get("ability_supported", True) for level in entry["levels"])]
        if not entries:
            raise ValueError("Catalogue vide après filtrage.")
        self.entries = entries
        self._cache: Dict[Tuple[str, int], Card] = {}

    def card(self, name: str, stars: int) -> Card:
        key = (name, stars)
        if key not in self._cache:
            self._cache[key] = Card(card_name=name, nb_stars=stars)
        return copy.deepcopy(self._cache[key])

    def deck(self, rng: random.Random, size: int = 4) -> List[Card]:
        return [self.card(entry["name"], entry["levels"][-1]["stars"])
                for entry in rng.sample(self.entries, size)]

    def matchup(self, rng: random.Random, size: int = 4) -> Tuple[List[Card], List[Card]]:
        """Deux decks tirés indépendamment (les deux camps n'ont donc pas la même main)."""
        return self.deck(rng, size), self.deck(rng, size)
