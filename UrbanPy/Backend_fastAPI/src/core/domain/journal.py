"""
Journal des effets d'un round : ce que le moteur applique, en français, entrée par entrée (« Amelia : bonus « -2 Opp
Power, Min 1 » → puissance d'Asporov 7 → 5 »). process_round ouvre un Journal le temps du round (`recording`) ; les
niveaux appellent `note(...)` sans connaître le journal ; hors enregistrement, `note` ne fait rien.
"""
from contextlib import contextmanager
from typing import Iterator, List, Optional

from src.core.domain.capacity import Capacity
from src.core.domain.card import Card

STAT_LABELS = {"power": "puissance", "damage": "dégâts", "attack": "attaque", "life": "vie", "pillz": "pillz"}


def label(capacity: Capacity) -> str:
    """Libellé d'une capacité de combat, posé par process_round (« pouvoir « Power +2 » ») ; repli sur son how."""
    return getattr(capacity, "label", None) or capacity.how or "effet"


def stat_change(stat: str, owner: str, before: int, after: int) -> str:
    return f"{STAT_LABELS.get(stat, stat)} {owner} {before} → {after}"


class Journal:
    def __init__(self, ally_card: Card, enemy_card: Card):
        self._sides = {id(ally_card): "ally", id(enemy_card): "enemy"}
        self.entries: List[dict] = []

    def note(self, card: Optional[Card], source: str, text: str) -> None:
        self.entries.append({"side": self._sides.get(id(card)) if card is not None else None,
                             "card": card.name if card is not None else None,
                             "source": source, "text": text})


_current: Optional[Journal] = None


@contextmanager
def recording(journal: Journal) -> Iterator[Journal]:
    global _current
    previous, _current = _current, journal
    try:
        yield journal
    finally:
        _current = previous


def note(card: Optional[Card], source: str, text: str) -> None:
    """Consigne une entrée dans le journal du round en cours ; no-op hors d'un round."""
    if _current is not None:
        _current.note(card, source, text)
