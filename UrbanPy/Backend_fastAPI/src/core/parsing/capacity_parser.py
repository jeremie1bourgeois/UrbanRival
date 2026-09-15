"""
Parseur des descriptions textuelles d'abilities / bonus (ex. "Growth: -1 Opp Power, Min 4")
vers des objets Capacity au vocabulaire exact du moteur. Fonction pure, ne lève jamais.
Voir docs/superpowers/specs/2026-09-15-capacity-parser-design.md.
"""
import re
from dataclasses import dataclass
from typing import Optional

from src.core.domain.capacity import Capacity


@dataclass(frozen=True)
class ParsedCapacity:
    capacity: Optional[Capacity]
    supported: bool
    reason: str = ""


NO_ABILITY = ParsedCapacity(capacity=None, supported=True, reason="no ability")

# Synonymes mot à mot (le point final est retiré avant la recherche)
_WORD_SYNONYMS = {
    "pow": "power", "dam": "damage", "dmg": "damage",
    "atk": "attack", "att": "attack",
    "mod": "modif",
    "prot": "protection", "protec": "protection", "protect": "protection",
    "canc": "cancel", "rec": "recover",
    "conf": "confidence", "vict": "victory", "def": "defeat",
}


def normalize(text: str) -> str:
    """Texte en minuscules, synonymes unifiés, ':' isolé par des espaces, virgules retirées."""
    t = text.lower().strip()
    t = t.replace("&", " and ").replace(";", ":")
    t = t.replace("pow/dam", "power and damage")
    t = re.sub(r"([+-])\s+(\d)", r"\1\2", t)          # "- 2" -> "-2"
    t = t.replace(",", " ")
    t = re.sub(r"\s*:\s*", " : ", t)                   # ':' devient un mot à part entière
    words = []
    for word in t.split():
        bare = word.rstrip(".")
        words.append(_WORD_SYNONYMS.get(bare, bare))
    t = " ".join(words)
    t = re.sub(r"^(-\d+) pillz opp\b", r"\1 opp pillz", t)
    return t


def _unsupported(reason: str) -> ParsedCapacity:
    return ParsedCapacity(capacity=None, supported=False, reason=reason)


def parse_capacity(text: str) -> ParsedCapacity:
    normalized = normalize(text or "")
    if normalized in ("", "no ability") or re.fullmatch(r"ability at level \d+", normalized):
        return NO_ABILITY
    return _unsupported("unknown core")
