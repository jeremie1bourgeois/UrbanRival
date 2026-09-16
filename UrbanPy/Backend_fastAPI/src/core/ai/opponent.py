"""
Adversaires automatiques. Un choix (Pick) suit la convention du moteur : pillz = 1 sans mise (attaque = puissance x pillz),
la fury coûte 3 pillz de plus. Fonctions pures : elles lisent la partie sans la modifier.

Quatre stratégies, de la plus faible à la plus forte : `random`, `heuristic` (règles simples, sans simulation),
`greedy` et `minimax` (un coup d'avance, simulé par l'API moteur `src/core/ai/engine.py` — voir `search_pick`).
`scripts/ai_arena.py` les fait s'affronter et donne leurs taux de victoire.
"""
import random
import statistics
from typing import Callable, List, Sequence

from src.core.ai.engine import FURY_COST, Pick, legal_actions, step
from src.core.ai.evaluation import evaluate
from src.core.domain.game import NB_ROUNDS, Game
from src.core.domain.player import Player

# Budget de simulation d'un coup : nombre de coups candidats évalués et de réponses adverses envisagées pour chacun.
# 48 x 9 ~ 430 rounds simulés, soit ~60 ms par décision (mesure : scripts/bench_engine.py).
MAX_CANDIDATES = 48
NB_REPLIES = 8


def _player(game: Game, side: str) -> Player:
    return game.enemy if side == "enemy" else game.ally


def _other(side: str) -> str:
    return "enemy" if side == "ally" else "ally"


def legal_picks(game: Game, side: str) -> List[Pick]:
    """Tous les choix jouables : cartes non jouées x pillz misables (0..disponibles) x fury si payable."""
    return legal_actions(game, side)


def random_pick(game: Game, side: str, rng: random.Random) -> Pick:
    return rng.choice(legal_picks(game, side))


def heuristic_pick(game: Game, side: str, rng: random.Random) -> Pick:
    """
    Joueur prudent : répartit ses pillz sur les rounds restants (tout au dernier), joue la carte au meilleur
    produit puissance x dégâts, garde la fury pour le dernier round s'il reste de quoi la payer.
    """
    player = _player(game, side)
    unplayed = [index for index, card in enumerate(player.cards) if not card.played]
    rounds_left = max(1, NB_ROUNDS - game.nb_turn + 1)
    card_index = max(unplayed, key=lambda index: (player.cards[index].power * player.cards[index].damage, -index))
    if rounds_left == 1:
        fury = player.pillz >= FURY_COST
        bet = player.pillz - (FURY_COST if fury else 0)
        return Pick(card_index, bet + 1, fury)
    bet = min(player.pillz, player.pillz // rounds_left + (1 if game.nb_turn >= 3 else 0))
    return Pick(card_index, bet + 1, False)


def search_pick(game: Game, side: str, rng: random.Random, aggregate: Callable[[Sequence[float]], float],
                max_candidates: int = MAX_CANDIDATES, nb_replies: int = NB_REPLIES) -> Pick:
    """
    Un coup d'avance : chaque coup candidat est joué contre un échantillon de réponses adverses, et les notes
    obtenues (`evaluation.evaluate`) sont résumées par `aggregate` — la moyenne pour un glouton (« en moyenne,
    quel coup rapporte le plus ? »), le minimum pour un minimax (« quel coup résiste à la pire réponse ? »).

    L'échantillonnage borne le coût : le round 1 offre ~92 coups à chaque joueur, soit 8 500 rounds à simuler
    pour une recherche exhaustive. Les candidats sont pris régulièrement (donc étalés sur les cartes et les
    mises), les réponses au hasard, la réponse heuristique de l'adversaire étant toujours du lot.
    À budget et graine égaux, la décision est reproductible.
    """
    candidates = _spread(legal_picks(game, side), max_candidates)
    replies = _sample_replies(game, _other(side), rng, nb_replies)
    best, best_score = None, None
    for candidate in candidates:
        scores = [evaluate(_step_for(game, side, candidate, reply), side) for reply in replies]
        score = aggregate(scores)
        if best_score is None or (score, -candidate.pillz) > (best_score, -best.pillz):
            best, best_score = candidate, score
    return best


def greedy_pick(game: Game, side: str, rng: random.Random) -> Pick:
    """Glouton : le coup qui rapporte le plus en moyenne contre les réponses envisagées."""
    return search_pick(game, side, rng, statistics.fmean)


def minimax_pick(game: Game, side: str, rng: random.Random) -> Pick:
    """Minimax à un coup : le coup dont la pire réponse adverse coûte le moins."""
    return search_pick(game, side, rng, min)


def _step_for(game: Game, side: str, own: Pick, opponent: Pick) -> Game:
    """État après le round, vu du camp `side` (le moteur attend toujours (allié, ennemi))."""
    ally, enemy = (own, opponent) if side == "ally" else (opponent, own)
    return step(game, ally, enemy, log=False)[0]


def _spread(picks: List[Pick], maximum: int) -> List[Pick]:
    """Au plus `maximum` choix, pris régulièrement dans la liste : toutes les cartes et un éventail de mises."""
    if len(picks) <= maximum:
        return picks
    return [picks[round(index * (len(picks) - 1) / (maximum - 1))] for index in range(maximum)]


def _sample_replies(game: Game, side: str, rng: random.Random, nb_replies: int) -> List[Pick]:
    """
    Réponses adverses envisagées. Les tirer uniformément parmi les coups légaux modélise un adversaire qui mise
    n'importe comment, et fait jouer n'importe comment : on envisage les coups d'un joueur raisonnable — sa
    réponse heuristique, et pour chaque carte qui lui reste ne rien miser, miser sa part du budget, la dépasser
    un peu, ou tout miser (fury comprise).
    """
    player = _player(game, side)
    rounds_left = max(1, NB_ROUNDS - game.nb_turn + 1)
    share = player.pillz // rounds_left
    replies = [heuristic_pick(game, side, rng)]
    for index, card in enumerate(player.cards):
        if card.played:
            continue
        for bet in sorted({0, share, share + 2, player.pillz}):
            if bet <= player.pillz:
                replies.append(Pick(index, bet + 1, False))
        if player.pillz >= FURY_COST:
            replies.append(Pick(index, player.pillz - FURY_COST + 1, True))
    unique = list(dict.fromkeys(replies))
    return unique if len(unique) <= nb_replies else unique[:1] + rng.sample(unique[1:], nb_replies - 1)


STRATEGIES = {
    "random": random_pick,
    "heuristic": heuristic_pick,
    "greedy": greedy_pick,
    "minimax": minimax_pick,
}
