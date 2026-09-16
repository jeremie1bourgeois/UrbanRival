"""
Adversaires automatiques. Un choix (Pick) suit la convention du moteur : pillz = 1 sans mise (attaque = puissance x pillz),
la fury coûte 3 pillz de plus. Fonctions pures : elles lisent la partie sans la modifier.
"""
import random
from dataclasses import dataclass
from typing import List

from src.core.domain.game import NB_ROUNDS, Game
from src.core.domain.player import Player

FURY_COST = 3


@dataclass(frozen=True)
class Pick:
    card_index: int
    pillz: int
    fury: bool = False


def _player(game: Game, side: str) -> Player:
    return game.enemy if side == "enemy" else game.ally


def legal_picks(game: Game, side: str) -> List[Pick]:
    """Tous les choix jouables : cartes non jouées x pillz misables (0..disponibles) x fury si payable."""
    player = _player(game, side)
    picks = []
    for index, card in enumerate(player.cards):
        if card.played:
            continue
        for bet in range(player.pillz + 1):
            picks.append(Pick(index, bet + 1, False))
            if bet + FURY_COST <= player.pillz:
                picks.append(Pick(index, bet + 1, True))
    return picks


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


STRATEGIES = {
    "random": random_pick,
    "heuristic": heuristic_pick,
}
