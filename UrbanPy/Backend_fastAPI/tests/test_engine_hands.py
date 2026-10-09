"""
Les mains aléatoires (src/core/engine/hands.py) nourrissent le corpus du moteur et, plus tard, ses datasets : elles ne
doivent contenir aucune carte dont le pouvoir n'est pas géré, car Card le remplace silencieusement par « pas de
pouvoir » et le moteur jouerait la carte sans lui.
"""
from src.adapters.repositories.card_repository import _official_cards
from src.core.engine.hands import _catalogue
from src.core.parsing.capacity_parser import parse_capacity


def test_every_drawable_level_has_a_supported_ability_and_bonus():
    official = _official_cards()
    for name, levels in _catalogue()[1].items():
        assert parse_capacity(official[name].get("bonus", "").strip()).supported, name
        for level in levels:
            assert parse_capacity(official[name][str(level)].get("ability", "").strip()).supported, (name, level)
