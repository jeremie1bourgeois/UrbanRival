"""Accès en lecture aux cartes officielles scrapées (data/jsonData_officiel.json), chargées une seule fois."""
import json
import os
from functools import lru_cache
from typing import Dict, Set, Tuple

from src.utils.config import BASE_DIR

OFFICIAL_CARDS_PATH = os.path.join(BASE_DIR, "data", "jsonData_officiel.json")


@lru_cache(maxsize=1)
def _official_cards() -> Dict[str, dict]:
    with open(OFFICIAL_CARDS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_official_card(card_name: str) -> Tuple[str, dict]:
    """Retourne (nom canonique, données brutes) ; recherche insensible à la casse."""
    wanted = card_name.lower()
    for name, data in _official_cards().items():
        if name.lower() == wanted:
            return name, data
    raise ValueError(f"No card found with name: {card_name}")


def all_capacity_descriptions() -> Set[str]:
    """Toutes les descriptions distinctes de bonus et d'abilities (tous niveaux d'étoiles)."""
    descriptions = set()
    for data in _official_cards().values():
        descriptions.add(data.get("bonus", "").strip())
        for level, star_data in data.items():
            if level.isdigit():
                descriptions.add(star_data.get("ability", "").strip())
    return descriptions
