import os

import pytest

from src.adapters.scraping.iclintz import card_links, clan_ids, parse_card_page, to_official_json

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "iclintz")


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as file:
        return file.read()


@pytest.fixture(scope="module")
def aamir():
    return parse_card_page(fixture("card_1334_aamir.html"), card_id=1334)


def test_clan_ids_are_read_from_the_navigation_menu():
    ids = clan_ids(fixture("home.html"))

    assert len(ids) == 36
    assert ids[:3] == [3, 4, 10] and 60 in ids


def test_card_links_are_unique_and_relative():
    links = card_links(fixture("clan_36_leader.html"))

    assert len(links) == 21
    assert all(link.startswith("/characters/card.php?ID=") for link in links)
    assert len(set(links)) == 21


def test_card_identity_comes_from_the_page_title(aamir):
    assert (aamir.id, aamir.name, aamir.faction, aamir.star_off) == (1334, "Aamir", "All Stars", 3)


def test_card_faction_is_the_last_dash_segment_of_the_title():
    html = fixture("card_1334_aamir.html").replace("iClintz | Aamir - All Stars", "iClintz | XU-B0t - Junkz")

    assert parse_card_page(html, card_id=1).faction == "Junkz"
    assert parse_card_page(html, card_id=1).name == "XU-B0t"


def test_card_levels_carry_stats_ability_and_image(aamir):
    assert [(level.stars, level.power, level.damage, level.ability) for level in aamir.levels] == [
        (1, 3, 4, "Ability at Level 3"),
        (2, 4, 4, "Ability at Level 3"),
        (3, 5, 4, "Growth: -1 Opp Power, Min 4"),
    ]
    assert all(level.image.startswith("https://") and level.image.endswith(".png") for level in aamir.levels)
    assert len({level.image for level in aamir.levels}) == 3


def test_card_bonus_and_clan_image(aamir):
    assert aamir.bonus == "-2 Opp Power, Min 1"
    assert aamir.clan_image == "https://s.acdn.ur-img.com/urimages/clan/ALLSTARS_42.png"


def test_versus_clans_are_rendered_as_text():
    card = parse_card_page(fixture("card_buf00n_versus.html"), card_id=2266)

    assert card.name == "Buf00n" and card.faction == "Hive"
    assert card.levels[-1].ability == "Versus Freaks, Oculus: -3 Opp. Life Min 0"


def test_official_json_keeps_the_historical_shape_and_adds_images(aamir):
    data = to_official_json([aamir])

    assert data["Aamir"]["faction"] == "All Stars"
    assert data["Aamir"]["starOff"] == 3
    assert data["Aamir"]["bonus"] == "-2 Opp Power, Min 1"
    assert data["Aamir"]["3"] == {"power": 5, "damage": 4, "ability": "Growth: -1 Opp Power, Min 4", "image": aamir.levels[2].image}
    assert data["Aamir"]["clan_image"] == aamir.clan_image
    assert data["Aamir"]["id"] == 1334


def test_official_json_keeps_the_first_of_two_homonyms(aamir):
    twin = parse_card_page(fixture("card_1334_aamir.html"), card_id=9999)

    data = to_official_json([aamir, twin])

    assert data["Aamir"]["id"] == 1334
