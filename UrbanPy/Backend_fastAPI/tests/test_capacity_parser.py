import pytest

from src.core.parsing.capacity_parser import ParsedCapacity, normalize, parse_capacity


# --- Normalisation ----------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Equalizer: -1 Opp Pow. & Dam., Min 1", "equalizer : -1 opp power and damage min 1"),
    ("Reprisal: -X Opp Pow. & Dmg,min Y", "reprisal : -x opp power and damage min y"),
    ("Stop: Atk. +3", "stop : attack +3"),
    ("-4 Opp Att. Per Life Left, Min 2", "-4 opp attack per life left min 2"),
    ("Courage; -2 Opp Pillz. Min 1", "courage : -2 opp pillz min 1"),
    ("-2 Pillz Opp. Min 1", "-2 opp pillz min 1"),
    ("Conf.: Vict. Or Def.: -2 Opp. Life, Min 1", "confidence : victory or defeat : -2 opp life min 1"),
    ("Backlash: - 2 Life Min 0", "backlash : -2 life min 0"),
    ("Power And Damage + 2", "power and damage +2"),
    ("Cancel Opp. Pow/dam Mod.", "cancel opp power and damage modif"),
    ("Reprisal: Cancel Opp Pow & Dam Mod", "reprisal : cancel opp power and damage modif"),
    ("Courage: Prot.: Power & Damage", "courage : protection : power and damage"),
    ("Revenge: Protec. Power And Dmg", "revenge : protection power and damage"),
    ("Versus  : Power +2", "versus : power +2"),
    ("Growth : Power & Damage +1", "growth : power and damage +1"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


# --- Pas d'ability ----------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["", "   ", "No Ability", "Ability at Level 3", "Ability at Level 5"])
def test_no_ability_is_supported_and_empty(text):
    parsed = parse_capacity(text)

    assert parsed == ParsedCapacity(capacity=None, supported=True, reason="no ability")
