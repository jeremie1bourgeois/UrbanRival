"""
Mains de 4 cartes tirées au hasard dans les cartes officielles, structurées comme les vraies (le bonus de clan
demande 2 cartes du clan) : mono-clan, 2 + 2, 3 + 1, ou quatre clans distincts pour la couverture ; parfois un
Leader ; tous niveaux d'étoiles. Reproductible par le générateur aléatoire passé en paramètre.
"""
import random
from functools import lru_cache
from typing import Dict, List, Tuple

from src.adapters.repositories.card_repository import _official_cards
from src.core.domain.card import Card

PATTERNS = ((4,), (2, 2), (3, 1), (1, 1, 1, 1))   # nombre de cartes par clan
LEADER = "Leader"
LEADER_RATE = 0.2                                   # part des mains où une carte est remplacée par un Leader


@lru_cache(maxsize=1)
def _catalogue() -> Tuple[Dict[str, List[str]], Dict[str, List[int]]]:
    """(noms par clan, niveaux jouables par nom), dans l'ordre du fichier officiel (reproductibilité)."""
    names_by_clan: Dict[str, List[str]] = {}
    levels_by_name: Dict[str, List[int]] = {}
    for name, card_data in _official_cards().items():
        names_by_clan.setdefault(card_data.get("faction", ""), []).append(name)
        levels_by_name[name] = [int(level) for level in card_data if level.isdigit()]
    return names_by_clan, levels_by_name


def _pick(rng: random.Random, clan: str, count: int) -> List[Tuple[str, int]]:
    """`count` cartes distinctes du clan, chacune à un niveau au hasard."""
    names_by_clan, levels_by_name = _catalogue()
    return [(name, rng.choice(levels_by_name[name])) for name in rng.sample(names_by_clan[clan], count)]


def random_hand(rng: random.Random) -> List[Card]:
    clans = [clan for clan in _catalogue()[0] if clan != LEADER]
    pattern = rng.choice(PATTERNS)
    hand = []
    for clan, count in zip(rng.sample(clans, len(pattern)), pattern):
        hand.extend(_pick(rng, clan, count))
    if rng.random() < LEADER_RATE:
        hand[-1] = _pick(rng, LEADER, 1)[0]
    rng.shuffle(hand)
    return [Card(name, level) for name, level in hand]
