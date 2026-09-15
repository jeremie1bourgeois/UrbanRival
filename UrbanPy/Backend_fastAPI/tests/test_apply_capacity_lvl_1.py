"""
Niveau 1 : stop / protection / copy / cancel / exchange. Scénario : Amelia (allié, P3 D5, idx 2) contre
Asporov (ennemi, P7 D3, idx 0), 1 pillz chacun. Abilities d'origine neutralisées, bonus de clan d'origine
(« -2 Opp Power, Min 1 », actifs : 4 et 3 All Stars en main) sauf texte passé en paramètre.
Sans capacité : Amelia power 1, Asporov power 5.
"""
import pytest

from src.core.parsing.capacity_parser import parse_capacity
from src.core.use_cases.process_round import process_round
from src.schemas.game_schemas import ProcessRoundInput

AMELIA, ASPOROV = 2, 0


def capacity(text):
    if text is None:
        return None
    parsed = parse_capacity(text)
    assert parsed.supported, parsed.reason
    return parsed.capacity


def play(game, ally_ability=None, enemy_ability=None, ally_bonus="-2 Opp Power, Min 1", enemy_bonus="-2 Opp Power, Min 1", turn=True, ally_pillz=1, enemy_pillz=1):
    amelia, asporov = game.ally.cards[AMELIA], game.enemy.cards[ASPOROV]
    amelia.ability, asporov.ability = capacity(ally_ability), capacity(enemy_ability)
    amelia.bonus, asporov.bonus = capacity(ally_bonus), capacity(enemy_bonus)
    game.turn = turn
    process_round(game, ProcessRoundInput(player1_card_index=AMELIA, player1_pillz=ally_pillz,
                                          player2_card_index=ASPOROV, player2_pillz=enemy_pillz))
    return amelia, asporov


# --- Stop -------------------------------------------------------------------------------------

def test_stop_opp_ability_cancels_the_opponent_ability(template_game):
    _, asporov = play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Power +2")

    assert asporov.power_fight == 7 - 2


def test_stop_opp_bonus_cancels_the_opponent_bonus(template_game):
    amelia, _ = play(template_game, ally_ability="Stop Opp. Bonus")

    assert amelia.power_fight == 3


def test_stop_capacities_are_consumed(template_game):
    amelia, _ = play(template_game, ally_ability="Stop Opp. Ability")

    assert amelia.ability_fight is None


def test_stops_resolve_simultaneously_soa_versus_sob(template_game):
    # Règle retenue (par défaut, à confirmer) : les deux Stops s'appliquent en même temps.
    amelia, asporov = play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Stop Opp. Bonus")

    assert (amelia.power_fight, asporov.power_fight) == (3 - 2, 7)   # A perd son bonus, B perd son ability


def test_conditional_stop_only_acts_when_its_condition_is_met(template_game):
    _, asporov = play(template_game, ally_ability="Courage: Stop Opp. Ability", enemy_ability="Power +2", turn=False)

    assert asporov.power_fight == 7 + 2 - 2


# --- Protection: Ability / Bonus --------------------------------------------------------------

def test_protection_ability_shields_the_ability_from_soa(template_game):
    _, asporov = play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Power +2", enemy_bonus="Protection: Ability")

    assert asporov.power_fight == 7 + 2 - 2


def test_sob_removes_protection_ability_then_soa_passes(template_game):
    _, asporov = play(template_game, ally_ability="Stop Opp. Ability", ally_bonus="Stop Opp. Bonus", enemy_ability="Power +2", enemy_bonus="Protection: Ability")

    assert asporov.power_fight == 7


def test_protection_bonus_shields_the_bonus_from_sob(template_game):
    amelia, _ = play(template_game, ally_ability="Stop Opp. Bonus", enemy_ability="Protection: Bonus")

    assert amelia.power_fight == 3 - 2


def test_soa_removes_protection_bonus_then_sob_passes(template_game):
    amelia, _ = play(template_game, ally_ability="Stop Opp. Ability", ally_bonus="Stop Opp. Bonus", enemy_ability="Protection: Bonus")

    assert amelia.power_fight == 3


def test_protection_bonus_survives_when_only_sob_is_present(template_game):
    # « Protection: Bonus » (ability) est elle-même protégée par « Protection: Ability » (bonus) : sans SoA, rien ne tombe.
    amelia, _ = play(template_game, ally_ability="Stop Opp. Bonus", enemy_ability="Protection: Bonus", enemy_bonus="Protection: Ability")

    assert amelia.power_fight == 3   # le bonus ennemi est « Protection: Ability », pas un malus : Amelia garde 3


# --- Copy: Opp. Ability / Bonus ---------------------------------------------------------------

def test_copy_opp_bonus_gains_the_opponent_bonus(template_game):
    _, asporov = play(template_game, ally_ability="Copy: Opp. Bonus")

    assert asporov.power_fight == 7 - 2 - 2   # bonus propre + bonus copié


def test_copy_opp_ability_gains_the_opponent_ability(template_game):
    amelia, _ = play(template_game, ally_ability="Copy: Opp. Ability", enemy_ability="Power +2")

    assert amelia.power_fight == 3 + 2 - 2


def test_copy_versus_copy_yields_nothing(template_game):
    amelia, asporov = play(template_game, ally_ability="Copy: Opp. Ability", enemy_ability="Copy: Opp. Ability")

    assert (amelia.power_fight, asporov.power_fight) == (1, 5)


def test_copied_stop_takes_part_in_the_stop_phase(template_game):
    _, asporov = play(template_game, ally_ability="Copy: Opp. Bonus", enemy_ability="Power +2", enemy_bonus="Stop Opp. Ability")

    assert asporov.power_fight == 7 - 2   # le SoA copié stoppe « Power +2 »


# --- Copy / Exchange de power et damage -------------------------------------------------------

def test_copy_opp_power_uses_the_printed_value(template_game):
    amelia, _ = play(template_game, ally_ability="Copy: Opp. Power")

    assert amelia.power_fight == 7 - 2


def test_copy_power_and_damage(template_game):
    amelia, _ = play(template_game, ally_ability="Copy: Power And Damage Opp.")

    assert (amelia.power_fight, amelia.damage_fight) == (7 - 2, 3)


def test_damage_exchange_swaps_printed_damages(template_game):
    amelia, asporov = play(template_game, ally_ability="Damage Exchange")

    assert (amelia.damage_fight, asporov.damage_fight) == (3, 5)


@pytest.mark.parametrize("text", ["Asymmetry: Copy: Opp. Power", "Confidence: Power Exchange", "Power And Damage Exchange"])
def test_value_copies_and_exchanges_do_not_crash(template_game, text):
    template_game.turn = True
    from src.core.domain.round import Round
    previous = Round(); previous.ally.win = True; template_game.history.append(previous)   # confidence satisfaite

    play(template_game, ally_ability=text)


# --- Cancel Opp. X Modif. ---------------------------------------------------------------------

def test_cancel_opp_power_modif_removes_every_opponent_power_modification(template_game):
    amelia, asporov = play(template_game, ally_ability="Cancel Opp. Power Modif.", enemy_ability="Power +2")

    assert (amelia.power_fight, asporov.power_fight) == (3, 7 - 2)   # ni le +2 adverse, ni le -2 sur Amelia


def test_cancel_opp_attack_modif(template_game):
    _, asporov = play(template_game, ally_ability="Cancel Opp. Attack Modif.", enemy_ability="Attack +5")

    assert asporov.attack == 5 * 1


def test_cancel_only_strips_the_cancelled_stat(template_game):
    amelia, _ = play(template_game, ally_ability="Cancel Opp. Power Modif.", enemy_ability="-1 Opp Power And Damage, Min 1", enemy_bonus="Protection: Ability")

    assert (amelia.power_fight, amelia.damage_fight) == (3, 5 - 1)


def test_cancel_opp_life_modif_removes_end_of_round_life_effects(template_game):
    play(template_game, ally_ability="Cancel Opp. Pillz & Life Modif.", enemy_ability="-2 Opp. Life, Min 0")   # Asporov gagne

    assert template_game.ally.life == 12 - 3


def test_cancel_capacities_are_consumed(template_game):
    amelia, _ = play(template_game, ally_ability="Cancel Opp. Life Modif.")

    assert amelia.ability_fight is None


# --- Protection: Power / Damage / Attack ------------------------------------------------------

def test_protection_power_shields_only_my_stat(template_game):
    amelia, asporov = play(template_game, ally_ability="Protection: Power", enemy_ability="Power +2")

    assert (amelia.power_fight, asporov.power_fight) == (3, 7 + 2 - 2)


def test_protection_power_and_damage(template_game):
    amelia, _ = play(template_game, ally_ability="Protection: Power And Damage", enemy_ability="-3 Opp Damage, Min 2")

    assert (amelia.power_fight, amelia.damage_fight) == (3, 5)


def test_protection_attack(template_game):
    amelia, _ = play(template_game, ally_ability="Protection: Attack", enemy_ability="-4 Opp Attack, Min 0")

    assert amelia.attack == 1


def test_protection_capacities_are_consumed(template_game):
    amelia, _ = play(template_game, ally_ability="Protection : Damage")

    assert amelia.ability_fight is None


# --- Condition « Stop: » : l'ability n'agit que si elle a été stoppée ----------------------------

def test_stop_conditioned_ability_fires_when_the_ability_is_stopped(template_game):
    amelia, _ = play(template_game, ally_ability="Stop: Power +3", enemy_ability="Stop Opp. Ability")

    assert amelia.power_fight == 3 + 3 - 2


def test_stop_conditioned_ability_does_nothing_when_not_stopped(template_game):
    amelia, _ = play(template_game, ally_ability="Stop: Power +3")

    assert amelia.power_fight == 3 - 2


def test_stop_conditioned_ability_does_not_fire_when_protected_from_the_stop(template_game):
    amelia, _ = play(template_game, ally_ability="Stop: Power +3", ally_bonus="Protection: Ability", enemy_ability="Stop Opp. Ability")

    assert amelia.power_fight == 3 - 2


def test_stop_conditioned_end_of_round_effect(template_game):
    play(template_game, ally_ability="Stop: +2 Life", enemy_ability="Stop Opp. Ability", ally_pillz=6)   # Amelia gagne

    assert template_game.ally.life == 14
