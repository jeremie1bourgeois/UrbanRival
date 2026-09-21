"""
Clan d'une carte en main : son propre clan, ou celui qu'un Oculus « Infiltrated » adopte. Partagé par process_round
(bonus, Leader unique) et multipliers (Support, Brawl).
"""
from collections import Counter

from src.core.domain.card import Card
from src.core.domain.player import Player

OCULUS = "Oculus"
LEADER = "Leader"


def is_infiltrated(card: Card) -> bool:
    return card.faction == OCULUS and card.bonus is not None and "infiltrated" in card.bonus.types


def _clan_for_infiltration(card: Card):
    """Chaque Leader est son propre clan : Freaks ×1 + Administrator + Ashigaru = trois clans, l'Oculus ne rejoint
    personne (combat 1347671, Support ×1) ; un Leader seul face à deux cartes d'un clan est la carte seule, l'Oculus
    le rejoint et le Cancel Leader l'annule (1346878 Morphun, 1347500 Ashigaru)."""
    return (LEADER, card.name) if card.faction == LEADER else card.faction


def infiltrated_clan(player: Player):
    """
    Clan adopté par l'Oculus « Infiltrated » de la main (règle officielle du bonus) : un seul autre clan -> celui-là ;
    deux autres clans -> celui de la carte seule ; trois autres clans ou plus d'un Oculus -> None.
    """
    oculus = [c for c in player.cards if c.faction == OCULUS]
    if len(oculus) != 1:
        return None
    counts = Counter(_clan_for_infiltration(c) for c in player.cards if c.faction != OCULUS)
    if len(counts) == 1:
        clan = next(iter(counts))
    elif len(counts) == 2:
        lone = [clan for clan, n in counts.items() if n == 1]
        clan = lone[0] if len(lone) == 1 else None
    else:
        clan = None
    return LEADER if isinstance(clan, tuple) else clan


def infiltrable_clans(card: Card):
    """Clans listés sur la carte Oculus (icônes de l'ability, condition « infiltrated:Clan|Clan ») ; None si inconnus."""
    if card.ability is None:
        return None
    for condition in card.ability.effect_conditions:
        if condition.startswith("infiltrated:"):
            return condition[len("infiltrated:"):].split("|")
    return None


def clan_for_bonus(player: Player, card: Card):
    """Clan dont la carte porte le bonus : son propre clan, ou le clan adopté pour un Oculus infiltré."""
    return infiltrated_clan(player) if is_infiltrated(card) else card.faction
