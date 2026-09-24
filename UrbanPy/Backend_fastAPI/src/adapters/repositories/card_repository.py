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


def all_image_urls() -> Set[str]:
    """Toutes les URLs d'images citées par le catalogue : illustrations par niveau et écussons de clan."""
    urls = set()
    for data in _official_cards().values():
        urls.add(data.get("clan_image", ""))
        for level, star_data in data.items():
            if level.isdigit():
                urls.add(star_data.get("image", ""))
    urls.discard("")
    return urls


@lru_cache(maxsize=1)
def official_card_catalogue() -> list:
    """
    Catalogue destiné au front : une entrée par carte avec ses niveaux jouables, et pour chaque
    capacité un drapeau indiquant si le moteur la gère (parseur) — importé ici pour éviter un import circulaire.
    """
    from src.core.parsing.capacity_parser import parse_capacity

    catalogue = []
    for name, data in _official_cards().items():
        levels = []
        for level in sorted((key for key in data if key.isdigit()), key=int):
            star_data = data[level]
            ability = star_data.get("ability", "").strip()
            levels.append({
                "stars": int(level),
                "power": int(str(star_data.get("power", 0)).strip()),
                "damage": int(str(star_data.get("damage", 0)).strip()),
                "ability": ability,
                "ability_supported": parse_capacity(ability).supported,
                "image": star_data.get("image", ""),
            })
        bonus = data.get("bonus", "").strip()
        catalogue.append({
            "name": name,
            "faction": data.get("faction", ""),
            "starOff": data.get("starOff", 0),
            "bonus": bonus,
            "bonus_supported": parse_capacity(bonus).supported,
            "clan_image": data.get("clan_image", ""),
            "levels": levels,
        })
    return catalogue
