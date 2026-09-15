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


from src.core.domain.capacity import Capacity


def cap(target, types, value, how="", borne=-1, conditions=()):
    return Capacity(target=target, types=list(types), value=value, borne=borne, how=how,
                    effect_conditions=list(conditions)).to_dict()


def parsed(text):
    result = parse_capacity(text)
    assert result.supported is True, result.reason
    return result.capacity.to_dict()


# --- Golden : encodage manuel du template (spec §3) -------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("-2 Opp Power, Min 1", cap("enemy", ["power"], -2, borne=1)),
    ("Growth: -1 Opp Power, Min 4", cap("enemy", ["power"], -1, how="growth", borne=4)),
    ("Courage: Damage +3", cap("ally", ["damage"], 3, conditions=["courage"])),
    ("Power +4", cap("ally", ["power"], 4)),
    ("-3 Opp Damage, Min 2", cap("enemy", ["damage"], -3, borne=2)),
    ("Support: Damage +1", cap("ally", ["damage"], 1, how="support")),
    ("Equalizer: -1 Opp Pow. & Dam., Min 1", cap("enemy", ["power", "damage"], -1, how="equalizer", borne=1)),
    ("Support: Attack +3", cap("ally", ["attack"], 3, how="support")),
])
def test_golden_template_encodings(text, expected):
    assert parsed(text) == expected


# --- Formes de cœur : modificateurs -----------------------------------------------------------

def test_stat_plus_with_max():
    assert parsed("Power +2, Max. 8") == cap("ally", ["power"], 2, borne=8)


def test_plus_life_targets_ally():
    assert parsed("+3 Life") == cap("ally", ["life"], 3)


def test_plus_pillz_and_life():
    assert parsed("+2 Pillz And Life") == cap("ally", ["pillz", "life"], 2)


def test_plus_players_life_targets_both():
    assert parsed("+2 Players Life") == cap("both", ["life"], 2)


def test_plus_opp_pillz_targets_enemy():
    assert parsed("Defeat: +2 Opp. Pillz") == cap("enemy", ["pillz"], 2, conditions=["defeat"])


def test_opp_attack_plus_targets_enemy():
    assert parsed("Opp. Attack +4") == cap("enemy", ["attack"], 4)


def test_minus_opp_life_and_pillz():
    assert parsed("Vict. Or Def.: -2 Opp Life & Pillz Min 1") == cap("enemy", ["pillz", "life"], -2, borne=1, conditions=["victory_defeat"])


def test_minus_self_life_backlash():
    assert parsed("Backlash: - 2 Life Min 0") == cap("ally", ["life"], -2, borne=0, conditions=["backlash"])


def test_minus_players_pillz_targets_both():
    assert parsed("-1 Players Pillz. Min 2") == cap("both", ["pillz"], -1, borne=2)


# --- Préfixes ---------------------------------------------------------------------------------

@pytest.mark.parametrize("prefix, condition", [
    ("Courage", "courage"), ("Revenge", "revenge"), ("Confidence", "confidence"), ("Reprisal", "reprisal"),
    ("Symmetry", "symmetry"), ("Asymmetry", "asymmetry"), ("Defeat", "defeat"), ("Backlash", "backlash"),
    ("Victory Or Defeat", "victory_defeat"), ("Conf.", "confidence"),
])
def test_condition_prefixes(prefix, condition):
    assert parsed(f"{prefix}: Attack +5") == cap("ally", ["attack"], 5, conditions=[condition])


@pytest.mark.parametrize("prefix", ["Support", "Growth", "Degrowth", "Equalizer", "Brawl"])
def test_multiplier_prefixes(prefix):
    assert parsed(f"{prefix}: -1 Opp Attack, Min 3") == cap("enemy", ["attack"], -1, how=prefix.lower(), borne=3)


def test_condition_and_multiplier_combine():
    assert parsed("Defeat: Growth: -1 Opp. Life, Min 2") == cap("enemy", ["life"], -1, how="growth", borne=2, conditions=["defeat"])


def test_two_conditions_combine():
    assert parsed("Conf.: Vict. Or Def.: -3 Opp. Life, Min 2") == cap("enemy", ["life"], -3, borne=2, conditions=["confidence", "victory_defeat"])


@pytest.mark.parametrize("prefix", ["Stop", "Killshot", "Day", "Team", "Versus", "Xantiax"])
def test_unsupported_prefixes(prefix):
    result = parse_capacity(f"{prefix}: Power +2")

    assert (result.capacity, result.supported, result.reason) == (None, False, f"unsupported prefix: {prefix.lower()}")


def test_unknown_prefix():
    result = parse_capacity("Wibble: Power +2")

    assert (result.supported, result.reason) == (False, "unknown prefix: wibble")


# --- Suffixe « per » --------------------------------------------------------------------------

@pytest.mark.parametrize("suffix, how", [
    ("Pillz Left", "nb_pillz_left"), ("Life Left", "nb_life_left"),
    ("Life Lost", "nb_life_lost"), ("Pillz Lost", "nb_pillz_lost"), ("Opp. Damage", "nb_dam_opp"),
])
def test_per_multipliers(suffix, how):
    assert parsed(f"+1 Attack Per {suffix}") == cap("ally", ["attack"], 1, how=how)


def test_per_with_max():
    assert parsed("+1 Power Per Life Left Max. 9") == cap("ally", ["power"], 1, how="nb_life_left", borne=9)


def test_minus_opp_per_life_left():
    assert parsed("-4 Opp Att. Per Life Left, Min 2") == cap("enemy", ["attack"], -4, how="nb_life_left", borne=2)


@pytest.mark.parametrize("suffix", ["Damage", "Round", "Opp. Power"])
def test_unsupported_per_multipliers(suffix):
    result = parse_capacity(f"+1 Life Per {suffix}")

    assert (result.supported, result.reason) == (False, f"unsupported multiplier: per {normalize(suffix)}")


def test_prefix_and_per_multiplier_is_rejected():
    result = parse_capacity("Growth: +1 Attack Per Pillz Left")

    assert (result.supported, result.reason) == (False, "unsupported: two multipliers")
