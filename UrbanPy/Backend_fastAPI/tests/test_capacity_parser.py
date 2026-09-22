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
    ("Stop: -1 Pillz Opp. Min 2", "stop : -1 opp pillz min 2"),
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
    ("Stop Opp. Bonus", cap("enemy", ["bonus"], 0, how="stop")),
    ("Support: Reanimate: +1 Life", cap("ally", ["reanimate"], 1, how="support")),
])
def test_golden_template_encodings(text, expected):
    assert parsed(text) == expected


def test_template_capacities_match_the_parser(template_data):
    for side in ("ally", "enemy"):
        for card in template_data[side]["cards"]:
            assert parse_capacity(card["ability_description"]).capacity.to_dict() == card["ability"], card["name"]
            assert parse_capacity(card["bonus_description"]).capacity.to_dict() == card["bonus"], card["name"]


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
    ("Unison", "unison"), ("Disunion", "disunion"),
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


def test_day_prefix_is_ignored_for_now():
    # Simplification assumée : le cycle jour/nuit n'est pas modélisé, « Day: » est toujours valide.
    assert parsed("Day: Power +2") == cap("ally", ["power"], 2)
    assert parsed("Day: Courage: Attack +3") == cap("ally", ["attack"], 3, conditions=["courage"])


@pytest.mark.parametrize("text, expected", [
    ("Stop: Power +3", cap("ally", ["power"], 3, conditions=["stop"])),
    ("Stop : -2 Opp Power, Min 3", cap("enemy", ["power"], -2, borne=3, conditions=["stop"])),
    ("Stop: Equalizer: - 2 Opp. Life Min 0", cap("enemy", ["life"], -2, how="equalizer", borne=0, conditions=["stop"])),
    ("Killshot: +3 Life", cap("ally", ["life"], 3, conditions=["killshot"])),
    ("Killshot: Toxin 1, Min 0", cap("enemy", ["toxine"], 1, borne=0, conditions=["killshot"])),
    ("Perfect: +2 Pillz", cap("ally", ["pillz"], 2, conditions=["perfect"])),
    ("Team: Perfect: -2 Opp. Life Min 0", cap("enemy", ["life"], -2, borne=0, conditions=["team", "perfect"])),
])
def test_stop_and_killshot_prefixes_are_deferred_conditions(text, expected):
    assert parsed(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Versus Freaks, Oculus: -3 Opp. Life Min 0", cap("enemy", ["life"], -3, borne=0, conditions=["versus:Freaks|Oculus"])),
    ("Versus All Stars: Power +2", cap("ally", ["power"], 2, conditions=["versus:All Stars"])),
    ("Courage: Versus Fang Pi Clang: Damage +2", cap("ally", ["damage"], 2, conditions=["courage", "versus:Fang Pi Clang"])),
])
def test_versus_prefix_keeps_the_clan_names(text, expected):
    assert parsed(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("After Oculus, Tolvack: Power +3", cap("ally", ["power"], 3, conditions=["after:Oculus|Tolvack"])),
    ("After Pussycats, Sakrohm: -4 Opp. Life Min 0", cap("enemy", ["life"], -4, borne=0, conditions=["after:Pussycats|Sakrohm"])),
    ("Infiltrated La Junta, Piranas: +1 Pillz And Life", cap("ally", ["pillz", "life"], 1, conditions=["infiltrated:La Junta|Piranas"])),
    ("Infiltrated Freaks: Courage: Damage +2", cap("ally", ["damage"], 2, conditions=["courage", "infiltrated:Freaks"])),
])
def test_after_and_infiltrated_prefixes_keep_the_clan_names(text, expected):
    assert parsed(text) == expected


def test_after_without_clan_is_unsupported():
    assert parse_capacity("After : Power +2").reason == "unsupported prefix: after"


def test_versus_without_clan_is_unsupported():
    result = parse_capacity("Versus  : Power +2")   # ancien scraping : le clan (une image) a été perdu

    assert (result.supported, result.reason) == (False, "unsupported prefix: versus")


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


@pytest.mark.parametrize("text, expected", [
    ("+1 Life Per Damage", cap("ally", ["life"], 1, how="nb_damage")),
    ("+1 Life Per Damage Max. 13", cap("ally", ["life"], 1, how="nb_damage", borne=13)),
    ("Confidence: +1 Life Per Dmg.", cap("ally", ["life"], 1, how="nb_damage", conditions=["confidence"])),
    ("+1 Pillz Per Damage", cap("ally", ["pillz"], 1, how="nb_damage")),
])
def test_per_damage_multiplier(text, expected):
    assert parsed(text) == expected


@pytest.mark.parametrize("suffix", ["Moon"])
def test_unsupported_per_multipliers(suffix):
    result = parse_capacity(f"+1 Life Per {suffix}")

    assert (result.supported, result.reason) == (False, f"unsupported multiplier: per {normalize(suffix)}")


def test_prefix_and_per_multiplier_is_rejected():
    result = parse_capacity("Growth: +1 Attack Per Pillz Left")

    assert (result.supported, result.reason) == (False, "unsupported: two multipliers")


# --- Niveau 1 : stop / copy / protection / cancel / exchange ---------------------------------

def test_stop_opp_bonus_golden():
    assert parsed("Stop Opp. Bonus") == cap("enemy", ["bonus"], 0, how="stop")


def test_stop_ability_without_opp():
    assert parsed("Confidence: Stop Ability") == cap("enemy", ["ability"], 0, how="stop", conditions=["confidence"])


@pytest.mark.parametrize("text, types", [
    ("Copy: Opp. Ability", ["ability"]), ("Copy: Opp. Bonus", ["bonus"]), ("Copy: Opp. Power", ["power"]),
    ("Copy: Opp. Damage", ["damage"]), ("Copy: Power And Damage Opp.", ["power", "damage"]),
    ("Reprisal: Copy Opp. Bonus", ["bonus"]),
])
def test_copy(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("enemy", types, "copy")


@pytest.mark.parametrize("text, types", [
    ("Protection: Ability", ["ability"]), ("Protection : Damage", ["damage"]), ("Protection: Attack", ["attack"]),
    ("Protection: Power And Damage", ["power", "damage"]), ("Courage: Bonus Protection", ["bonus"]),
    ("Courage: Prot.: Power & Damage", ["power", "damage"]), ("Revenge: Protec. Power And Dmg", ["power", "damage"]),
])
def test_protection(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("ally", types, "Protection")


@pytest.mark.parametrize("text, types", [
    ("Cancel Opp. Power Modif.", ["power"]), ("Cancel Opp. Pillz & Life Modif.", ["pillz", "life"]),
    ("Cancel Opp. Pow/dam Mod.", ["power", "damage"]), ("Reprisal: Cancel Opp Pow & Dam Mod", ["power", "damage"]),
    ("Day: Courage: Canc. Power & Dam. Mod", ["power", "damage"]),
])
def test_cancel(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("enemy", types, "cancel")


@pytest.mark.parametrize("text, types", [
    ("Power Exchange", ["power"]), ("Damage Exchange", ["damage"]), ("Power And Damage Exchange", ["power", "damage"]),
])
def test_exchange(text, types):
    assert parsed(text) == cap("both", types, 0, how="exchange")


@pytest.mark.parametrize("text, expected", [
    ("Power Impose", cap("enemy", ["power"], 0, how="impose")),
    ("Reprisal: Damage Impose", cap("enemy", ["damage"], 0, how="impose", conditions=["reprisal"])),
])
def test_impose(text, expected):
    assert parsed(text) == expected


@pytest.mark.parametrize("text, expected", [
    # « Cards » : les deux cartes du round (règle officielle : « The Damage points of both characters are reduced… »)
    ("-2 Cards Damage, Min 1", cap("both", ["damage"], -2, borne=1)),
    ("-7 Cards Attack, Min 0", cap("both", ["attack"], -7, borne=0)),
    ("Cards Damage +2", cap("both", ["damage"], 2)),
    ("Support: -1 Cards Damage, Min 0", cap("both", ["damage"], -1, how="support", borne=0)),
    ("Confidence: -4 Cards Damage, Min 0", cap("both", ["damage"], -4, borne=0, conditions=["confidence"])),
    ("Protection: Cards Power And Damage", cap("both", ["power", "damage"], 0, how="Protection")),
])
def test_cards_effects_target_both_cards(text, expected):
    assert parsed(text) == expected


def test_tune_out_is_a_resolution_mode():
    assert parsed("Tune Out") == cap("both", ["tune_out"], 0, how="tune_out")


# --- Niveau 4 : effets persistants ------------------------------------------------------------

@pytest.mark.parametrize("text, target, types", [
    ("Poison 2, Min 1", "enemy", ["poison"]), ("Toxin 1, Min 3", "enemy", ["toxine"]),
    ("Heal 2 Max. 10", "ally", ["heal"]), ("Regen 1, Max. 12", "ally", ["regen"]), ("Dope 1, Max. 8", "ally", ["dope"]),
])
def test_persistent_effects(text, target, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["value"], result["borne"]) == (target, types, int(text.split()[1].rstrip(",")), int(text.split()[-1]))


@pytest.mark.parametrize("text, expected", [
    ("Consume 1, Min 3", cap("enemy", ["consume"], 1, borne=3)),
    ("Repris.: Consume 1, Min 4", cap("enemy", ["consume"], 1, borne=4, conditions=["reprisal"])),
    ("Combust 1, Min 2", cap("enemy", ["combust"], 1, borne=2)),
    ("Players Combust 1, Min 0", cap("both", ["combust"], 1, borne=0)),
    ("Victory Or Defeat: Combust 1, Min 3", cap("enemy", ["combust"], 1, borne=3, conditions=["victory_defeat"])),
    ("Mindwipe 1, Min 3", cap("enemy", ["combust"], 1, borne=3)),            # même effet que Combust d'après les textes officiels
    ("Confidence: Mindwipe 2, Min 0", cap("enemy", ["combust"], 2, borne=0, conditions=["confidence"])),
    ("Victory Or Defeat: Corrosion 1, Min 0", cap("enemy", ["poison"], 1, how="growth", borne=0, conditions=["victory_defeat"])),   # poison x numéro du round
])
def test_new_persistent_effects(text, expected):
    assert parsed(text) == expected


def test_xantiax_hits_both_players_win_or_lose():
    assert parsed("Xantiax: -3 Life, Min. 5") == cap("both", ["life"], -3, borne=5, conditions=["victory_defeat"])


def test_corrupt_costs_the_owner_life_win_or_lose():
    assert parsed("Corrupt 2 Min. 5") == cap("ally", ["life"], -2, borne=5, conditions=["victory_defeat"])


def test_growth_poison_keeps_multiplier():
    assert parsed("Growth: Poison 1, Min 2") == cap("enemy", ["poison"], 1, how="growth", borne=2)


# --- Reanimate --------------------------------------------------------------------------------

def test_reanimate_golden():
    assert parsed("Support: Reanimate: +1 Life") == cap("ally", ["reanimate"], 1, how="support")


from src.adapters.repositories.card_repository import all_capacity_descriptions


@pytest.mark.parametrize("text, keyword", [
    ("Rebirth 2, Max. 10", "rebirth"),     ("Remove Ability Conditions", "remove ability conditions"), ("Beyond", "beyond"),
])
def test_explicitly_unsupported_cores(text, keyword):
    result = parse_capacity(text)

    assert (result.capacity, result.supported, result.reason) == (None, False, f"unsupported core: {keyword}")


def test_gibberish_is_unknown_core():
    assert parse_capacity("Blorp the flurb").reason == "unknown core"


# --- Couverture sur les descriptions officielles -----------------------------------------

SUPPORTED_DESCRIPTIONS_FLOOR = 1386  # mesuré le 2026-09-16 sur 1396 descriptions ; à relever quand la couverture progresse


def test_every_official_description_parses_without_raising():
    descriptions = all_capacity_descriptions()
    results = {text: parse_capacity(text) for text in descriptions}   # ne doit pas lever

    assert len(descriptions) == 1395   # instantané iclintz du 2026-09-15, clans « After » et « Infiltrated » rendus en texte le 2026-09-16, bonus GhosTown de Gunslinger ramené au texte de jour le 2026-09-22
    assert all(r.reason for r in results.values() if not r.supported)
    supported = sum(1 for r in results.values() if r.supported)
    assert supported >= SUPPORTED_DESCRIPTIONS_FLOOR, f"couverture en baisse : {supported} < {SUPPORTED_DESCRIPTIONS_FLOOR}"


@pytest.mark.parametrize("text, expected", [
    # Leaders : « Per Round » = à chaque round, victoire ou défaite, pour la carte jouée (comme un Team:)
    ("+1 Pillz Per Round", cap("ally", ["pillz"], 1, conditions=["team", "victory_defeat"])),
    ("-1 Opp. Pillz, Per Round, Min 4", cap("enemy", ["pillz"], -1, borne=4, conditions=["team", "victory_defeat"])),
    ("Team: Cancel Players Dam. Mod.", cap("both", ["damage"], 0, how="cancel", conditions=["team"])),
    ("Team: Cancel Players Life Mod.", cap("both", ["life"], 0, how="cancel", conditions=["team"])),
    ("Tie-break", cap("ally", ["tie_break"], 0, how="tie_break", conditions=["team"])),
    ("Recover 1 Players Pillz Out Of 2", cap("both", ["recover"], 1, borne=2)),
])
def test_leader_and_players_variants(text, expected):
    assert parsed(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Fatal Killshot", cap("enemy", ["ko"], 0, conditions=["killshot"])),
    ("Infiltrated GHEIST, Zenith: Fatal Killshot", cap("enemy", ["ko"], 0, conditions=["infiltrated:GHEIST|Zenith", "killshot"])),
    ("Sinister Symmetry", cap("enemy", ["ko"], 0, conditions=["symmetry"])),
])
def test_instant_win_abilities(text, expected):
    assert parsed(text) == expected


def test_counter_attack_and_limitless_are_leader_modes():
    assert parsed("Counter-attack") == cap("ally", ["counter_attack"], 0, how="counter_attack", conditions=["team"])
    assert parsed("Limitless") == cap("ally", ["limitless"], 0, how="limitless", conditions=["team"])


def test_team_prefix_is_a_leader_condition():
    assert parsed("Team: Courage: Power +3") == cap("ally", ["power"], 3, conditions=["team", "courage"])
    assert parsed("Team: +7 Attack") == cap("ally", ["attack"], 7, conditions=["team"])


# --- Formes rencontrées dans les données 2026 -------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Rev: Power +2", cap("ally", ["power"], 2, conditions=["revenge"])),
    ("Repris: Damage +2", cap("ally", ["damage"], 2, conditions=["reprisal"])),
    ("Asym: Attack +4", cap("ally", ["attack"], 4, conditions=["asymmetry"])),
    ("Asymm: Attack +4", cap("ally", ["attack"], 4, conditions=["asymmetry"])),
    ("Brwl: -1 Opp Power, Min 3", cap("enemy", ["power"], -1, how="brawl", borne=3)),
    ("+1 Attack / Life Lost", cap("ally", ["attack"], 1, how="nb_life_lost")),
    ("+1 Dam./ Life Lost Max. 6", cap("ally", ["damage"], 1, how="nb_life_lost", borne=6)),
    ("Repair 1, Max. 12", cap("ally", ["repair"], 1, borne=12)),
    ("Bet > 4 pillz: -3 Opp. Life, Min 2", cap("enemy", ["life"], -3, borne=2, conditions=["bet>4"])),
    ("Bet < 6 pillz: Power +3", cap("ally", ["power"], 3, conditions=["bet<6"])),
])
def test_abbreviations_repair_and_bet(text, expected):
    assert parsed(text) == expected


def test_night_prefix_is_inert_since_day_is_always_valid():
    result = parse_capacity("Night: Power +2")

    assert (result.supported, result.reason) == (False, "unsupported prefix: night")


@pytest.mark.parametrize("text, keyword", [
    ("Overdose", "overdose"), ("Perfection", "perfection"), ])
def test_new_unsupported_cores_have_a_named_reason(text, keyword):
    assert parse_capacity(text).reason == f"unsupported core: {keyword}"


# --- Recover, Cancel Leader, per opp power, Infiltrated -------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Defeat: Recover 2 Pillz Out Of 3", cap("ally", ["recover"], 2, borne=3, conditions=["defeat"])),
    ("Recover 1 Pillz Out Of 2", cap("ally", ["recover"], 1, borne=2)),
    ("Team: Defeat: Rec. 1 Pillz Out Of 2", cap("ally", ["recover"], 1, borne=2, conditions=["team", "defeat"])),
    ("+1 Attack Per Opp. Power", cap("ally", ["attack"], 1, how="nb_pow_opp")),
    ("Revenge: + 2 Attack Per Opp. Power", cap("ally", ["attack"], 2, how="nb_pow_opp", conditions=["revenge"])),
    ("Infiltrated", cap("ally", ["infiltrated"], 0)),
])
def test_recover_per_opp_power_and_infiltrated(text, expected):
    assert parsed(text) == expected


def test_cancel_leader_is_handled_by_the_single_leader_rule():
    result = parse_capacity("Cancel Leader")

    assert (result.capacity, result.supported) == (None, True)
    assert "leader" in result.reason
