"""
Solveur exact de fin de partie : induction arrière mémoïsée sur l'état public (docs/IA.md, étape 2).

Entre deux rounds, tout est public ; dans un round, le second joueur voit la carte du premier, pas sa mise.
Un round se résout donc **par carte du premier joueur** : pour chaque carte `c` qu'il peut poser, un jeu
matriciel (ses mises sur `c`) × (carte et mise du second) dont les cellules valent la valeur de l'état suivant ;
le premier pose la carte de meilleure valeur (choix pur) et tire sa mise au sort dans la stratégie mixte de ce
jeu ; le second répond à la carte vue par la stratégie colonne du jeu de cette carte.

Les valeurs sont celles de l'allié : +1 partie gagnée, -1 perdue, 0 nulle (`engine.reward`).

Mémoïsation sur une clé canonique de l'état public (`canonical_key`) : deux chemins qui mènent au même état
(mêmes mains, vies, pillz, cartes jouées, effets persistants, résultat du round précédent, premier joueur)
partagent la solution. Le cache est global au processus ; `clear_cache()` le vide.
"""
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.core.ai import engine, round_matrix
from src.core.ai.engine import Pick
from src.core.ai.equilibrium import solve_matrix
from src.core.domain.game import NB_ROUNDS, Game

# Rounds résolus exactement (les deux derniers) ; avant, la stratégie `solver` joue le coup du minimax (étape 4 :
# recherche à profondeur limitée).
EXACT_ROUNDS = 2


@dataclass(frozen=True)
class Solution:
    """Équilibre d'un round : ce que joue le premier joueur, ce que répond le second à chaque carte possible."""
    first: str                              # camp qui pose en premier
    value: float                            # valeur de l'état pour l'allié
    card: int                               # carte posée par le premier joueur (choix pur)
    bets: Dict[Pick, float]                 # mises du premier joueur sur cette carte, probabilités > 0
    replies: Dict[int, Dict[Pick, float]]   # réponse mixte du second à chaque carte que le premier peut poser
    card_values: Dict[int, float]           # valeur pour l'allié si le premier pose chaque carte


_cache: Dict[tuple, Solution] = {}


def solve(state: Game) -> Solution:
    key = canonical_key(state)
    solution = _cache.get(key)
    if solution is None:
        solution = _cache[key] = _solve(state)
    return solution


def clear_cache() -> None:
    _cache.clear()


def canonical_key(state: Game) -> tuple:
    """
    Tout ce que le moteur lit pour jouer la suite de la partie : round et premier joueur, puis par camp vies,
    pillz, cartes (identité et jouée ou non), effets persistants ; enfin le résultat et les cartes du round
    précédent (conditions Revenge / Confidence / After).
    """
    last = state.history[-1] if state.history else None
    return (state.nb_turn, state.turn,
            _player_key(state.ally), _player_key(state.enemy),
            None if last is None else (last.ally.card_index, last.ally.win, last.enemy.card_index, last.enemy.win))


def _player_key(player) -> tuple:
    return (player.life, player.pillz,
            tuple((card.name, card.stars, card.played) for card in player.cards),
            tuple(sorted((effect.kind, effect.value, effect.borne) for effect in player.effect_list)))


def _solve(state: Game) -> Solution:
    first = engine.first_side(state)
    second = engine.other(first)
    sign = 1 if first == "ally" else -1        # la ligne du LP maximise : les gains sont ceux du premier joueur
    columns = engine.legal_actions(state, second)
    card_values, bets_by_card, replies = {}, {}, {}
    for card, rows in _picks_by_card(engine.legal_actions(state, first)).items():
        cells = {}
        for second_card in _picks_by_card(columns):
            cells.update(round_matrix.values(state, first, card, second_card, value))
        matrix = [[sign * cells[(row, column)] for column in columns] for row in rows]
        equilibrium = solve_matrix(matrix)
        card_values[card] = sign * equilibrium.value
        bets_by_card[card] = _support(rows, equilibrium.row)
        replies[card] = _support(columns, equilibrium.column)
    best = max(card_values, key=lambda card: sign * card_values[card])
    return Solution(first=first, value=card_values[best], card=best, bets=bets_by_card[best],
                    replies=replies, card_values=card_values)


def solver_pick(game: Game, side: str, rng: random.Random, revealed_card: Optional[int] = None) -> Pick:
    """
    Stratégie « solver » (signature commune, voir `opponent.STRATEGIES`) : exacte sur les deux derniers rounds —
    en premier, la carte de l'équilibre et une mise tirée au sort dans sa stratégie mixte ; en second, la réponse
    mixte à la carte vue (à défaut de carte révélée, à celle que l'équilibre ferait poser). Avant, le minimax.
    """
    if NB_ROUNDS - game.nb_turn + 1 > EXACT_ROUNDS:
        from src.core.ai.opponent import minimax_pick      # import local : opponent enregistre solver_pick
        return minimax_pick(game, side, rng, revealed_card=revealed_card)
    return _draw(distribution(game, side, revealed_card), rng)


def distribution(game: Game, side: str, revealed_card: Optional[int] = None) -> Dict[Pick, float]:
    """
    La politique du solveur sous forme de probabilités (interface des politiques, voir `exploitability`) :
    en premier, la carte de l'équilibre et ses mises ; en second, la réponse à la carte vue.
    """
    if NB_ROUNDS - game.nb_turn + 1 > EXACT_ROUNDS:
        raise ValueError(f"Round {game.nb_turn} is not solved exactly (only the last {EXACT_ROUNDS} rounds are)")
    solution = solve(game)
    if engine.plays_first(game, side):
        return solution.bets
    return solution.replies[solution.card if revealed_card is None else revealed_card]


def value(state: Game) -> float:
    """Valeur de l'état pour l'allié : la récompense si la partie est finie, sinon celle de l'équilibre."""
    if engine.is_terminal(state):
        return engine.reward(state, "ally")
    return solve(state).value


def _picks_by_card(picks: List[Pick]) -> Dict[int, List[Pick]]:
    by_card: Dict[int, List[Pick]] = {}
    for pick in picks:
        by_card.setdefault(pick.card_index, []).append(pick)
    return by_card


def _draw(moves: Dict[Pick, float], rng: random.Random) -> Pick:
    """Un coup tiré au sort selon ses probabilités (le dernier absorbe l'arrondi)."""
    threshold = rng.random() * sum(moves.values())
    for pick, probability in moves.items():
        threshold -= probability
        if threshold < 0:
            return pick
    return pick


def _support(picks: List[Pick], probabilities, epsilon: float = 1e-9) -> Dict[Pick, float]:
    """Les coups de probabilité non nulle (le LP renvoie des zéros numériques)."""
    return {pick: float(p) for pick, p in zip(picks, probabilities) if p > epsilon}
