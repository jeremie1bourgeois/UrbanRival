"""
API moteur pure (feuille de route D1) : un état (`Game`), deux actions (`Pick`), un pas (`step`).

Aucune persistance, aucun I/O, aucune dépendance à FastAPI : c'est la surface sur laquelle se branchent les
adversaires de recherche (`src/core/ai/opponent.py`) et, plus tard, un environnement d'apprentissage.

    state = engine.new_game(mes_cartes, ses_cartes)
    while not engine.is_terminal(state):
        state, result = engine.step(state, mon_choix, son_choix)
    engine.reward(state, "ally")   # +1 victoire, -1 défaite, 0 nulle

Convention des actions, identique à celle du moteur : `pillz` compte la pillz toujours consommée (attaque =
puissance × pillz), donc `pillz = 1` signifie « aucune mise » ; la fury coûte 3 pillz de plus.
"""
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple

from src.core.domain.game import NB_ROUNDS, Game
from src.core.domain.player import Player
from src.core.domain.round import Round
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput

FURY_COST = 3
STARTING_LIFE = 12
STARTING_PILLZ = 12
SIDES = ("ally", "enemy")


@dataclass(frozen=True)
class Pick:
    """Un choix de joueur : la carte jouée, les pillz (mise + 1), la fury."""
    card_index: int
    pillz: int
    fury: bool = False


@dataclass(frozen=True)
class StepResult:
    """Ce que le round a produit : son résultat, l'état de la partie après coup, le journal des effets."""
    round: Round
    result: GameResult
    done: bool
    log: List[dict] = field(default_factory=list)


def new_game(ally_cards: Sequence[Tuple[str, int]], enemy_cards: Sequence[Tuple[str, int]],
             life: int = STARTING_LIFE, pillz: int = STARTING_PILLZ) -> Game:
    """Partie prête à jouer (round 1) à partir de deux mains `[(nom de carte, étoiles), ...]`, sans rien écrire."""
    from src.core.domain.card import Card      # import local : Card lit les données officielles au chargement

    ally = Player(name="ally", life=life, pillz=pillz,
                  cards=[Card(card_name=name, nb_stars=stars) for name, stars in ally_cards])
    enemy = Player(name="enemy", life=life, pillz=pillz,
                   cards=[Card(card_name=name, nb_stars=stars) for name, stars in enemy_cards])
    return Game(1, True, ally, enemy, [])


def clone(state: Game) -> Game:
    """Copie indépendante d'un état. Passe par `to_dict` : cinq fois plus rapide qu'un `deepcopy`."""
    return Game.from_dict_template(state.to_dict())


def player(state: Game, side: str) -> Player:
    if side not in SIDES:
        raise ValueError(f"Unknown side: {side!r} (expected one of {SIDES})")
    return state.ally if side == "ally" else state.enemy


def legal_actions(state: Game, side: str) -> List[Pick]:
    """Tous les choix jouables : cartes non jouées × pillz misables (0..disponibles) × fury si payable."""
    if is_terminal(state):
        return []
    own = player(state, side)
    actions = []
    for index, card in enumerate(own.cards):
        if card.played:
            continue
        for bet in range(own.pillz + 1):
            actions.append(Pick(index, bet + 1, False))
            if bet + FURY_COST <= own.pillz:
                actions.append(Pick(index, bet + 1, True))
    return actions


def step(state: Game, ally_action: Pick, enemy_action: Pick, *, in_place: bool = False,
         log: bool = True) -> Tuple[Game, StepResult]:
    """
    Joue un round et renvoie (état après le round, résultat). L'état reçu n'est pas modifié sauf `in_place=True`.
    `log=False` saute le journal des effets (~7 % de temps en moins ; l'état produit est le même).
    Lève ValueError si l'un des choix est illégal.
    """
    round_data = ProcessRoundInput(
        player1_card_index=ally_action.card_index, player1_pillz=ally_action.pillz, player1_fury=ally_action.fury,
        player2_card_index=enemy_action.card_index, player2_pillz=enemy_action.pillz, player2_fury=enemy_action.fury)
    check_round_correct(state, round_data)

    next_state = state if in_place else clone(state)
    process_round(next_state, round_data, log=log)

    played = next_state.history[-1]
    return next_state, StepResult(round=played, result=result(next_state),
                                  done=is_terminal(next_state), log=played.log)


def is_terminal(state: Game) -> bool:
    """La partie est finie : quatre rounds joués, ou un joueur à 0 vie."""
    return result(state) is not GameResult.NONE


def result(state: Game) -> GameResult:
    """
    Résultat de la partie : victoire aux vies après NB_ROUNDS rounds, ou dès qu'un joueur tombe à 0
    (double KO au cours de la partie : l'allié est déclaré perdant — comportement historique de `check_end`).
    """
    if state.nb_turn > NB_ROUNDS:
        if state.ally.life > state.enemy.life:
            return GameResult.ALLY
        if state.ally.life < state.enemy.life:
            return GameResult.ENEMY
        return GameResult.DRAW
    if state.ally.life <= 0:
        return GameResult.ENEMY
    if state.enemy.life <= 0:
        return GameResult.ALLY
    return GameResult.NONE


def reward(state: Game, side: str) -> int:
    """Récompense de fin de partie pour un camp : +1 victoire, -1 défaite, 0 nulle ou partie en cours."""
    outcome = result(state)
    if outcome is GameResult.NONE or outcome is GameResult.DRAW:
        return 0
    winner = "ally" if outcome is GameResult.ALLY else "enemy"
    return 1 if winner == side else -1


def play_out(state: Game, strategies: dict, rng, in_place: bool = False) -> Game:
    """
    Déroule la partie jusqu'à la fin, chaque camp jouant sa stratégie `(game, side, rng) -> Pick`
    (voir `src/core/ai/opponent.STRATEGIES`). Renvoie l'état final.
    """
    current = state if in_place else clone(state)
    while not is_terminal(current):
        ally_action = strategies["ally"](current, "ally", rng)
        enemy_action = strategies["enemy"](current, "enemy", rng)
        current, _ = step(current, ally_action, enemy_action, in_place=True, log=False)
    return current


def actions_of(picks: Iterable[Pick]) -> List[Tuple[int, int, bool]]:
    """Représentation « plate » des actions, pour un espace d'actions d'apprentissage."""
    return [(pick.card_index, pick.pillz, pick.fury) for pick in picks]
