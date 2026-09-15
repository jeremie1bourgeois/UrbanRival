import pytest

from src.core.domain.card import Card
from src.core.domain.capacity import Capacity


def test_card_is_built_from_official_data_with_parsed_capacities():
    card = Card("Aamir", 3)

    assert (card.name, card.faction, card.stars, card.starOff) == ("Aamir", "All Stars", 3, 3)
    assert (card.power, card.damage) == (5, 4)                      # "5 " / "4 " dans le JSON
    assert (card.ability_description, card.bonus_description) == ("Growth: -1 Opp Power, Min 4", "-2 Opp Power, Min 1")
    assert card.ability.to_dict() == Capacity("enemy", ["power"], -1, 4, how="growth").to_dict()
    assert card.bonus.to_dict() == Capacity("enemy", ["power"], -2, 1).to_dict()
    assert (card.power_fight, card.damage_fight, card.pillz_fight, card.attack) == (0, 0, 0, 0)
    assert (card.ability_fight, card.bonus_fight, card.fury, card.played, card.win) == (None, None, False, False, False)


def test_card_name_lookup_is_case_insensitive():
    assert Card("aamir", 3).name == "Aamir"


def test_unknown_card_raises():
    with pytest.raises(ValueError, match="No card found"):
        Card("Zorglub", 1)


def test_missing_star_level_raises():
    with pytest.raises(ValueError, match="No data for 5 stars"):
        Card("Aamir", 5)


def test_ability_locked_at_lower_level_is_none():
    card = Card("Aamir", 1)

    assert (card.ability, card.ability_description) == (None, "Ability at Level 3")


def test_unsupported_ability_is_none_but_description_is_kept():
    card = Card("Raoul", 2)   # "Killshot: +5 Life" : préfixe hors moteur

    assert card.ability is None
    assert card.ability_description == "Killshot: +5 Life"


def test_card_with_no_ability_round_trips_through_json():
    card = Card("Aamir", 1)

    restored = Card.from_dict_template(card.to_dict())

    assert restored.ability is None
    assert restored.to_dict() == card.to_dict()
