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
    amelia.ability_description, asporov.ability_description = ally_ability or "", enemy_ability or ""
    amelia.bonus_description, asporov.bonus_description = ally_bonus or "", enemy_bonus or ""
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


# Règle officielle (support UR, article 91) : « There are no priorities. […] check that nothing is blocking it and if this
# is the case, that nothing is blocking the Ability/Bonus block, just like a chain. » -> un Stop stoppé ne stoppe rien.

def test_official_example_1_my_sob_bonus_blocks_the_soa_bonus_so_my_ability_applies(template_game):
    # « your character has +8 Attack as his ability and Stop Bonus as his Bonus, his opponent has Stop Ability as his
    #   Bonus. Is your Ability activated? Yes »
    amelia, _ = play(template_game, ally_ability="Attack +8", ally_bonus="Stop Opp. Bonus", enemy_bonus="Stop Opp. Ability")

    assert amelia.attack == 3 + 8


def test_official_example_2_my_soa_ability_blocks_the_sob_ability_so_my_bonus_applies(template_game):
    # « your character has +2 Power as his Bonus and Stop Opp Ability as his Ability, his opponent has Stop Opp Bonus as
    #   his Ability. Is your Ability activated? Yes »
    amelia, _ = play(template_game, ally_ability="Stop Opp. Ability", ally_bonus="Power +2", enemy_ability="Stop Opp. Bonus", enemy_bonus=None)

    assert amelia.power_fight == 3 + 2


def test_soa_ability_versus_sob_ability_the_soa_wins_the_chain(template_game):
    amelia, asporov = play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Stop Opp. Bonus")

    assert (amelia.power_fight, asporov.power_fight) == (3 - 2, 7 - 2)   # rien ne bloque le SoA ; il bloque le SoB ; le bonus d'Amelia frappe


def test_soa_versus_soa_is_a_cycle_where_both_stops_win(template_game):
    # Chaîne infinie, non documentée : les Stops gagnent, les deux abilities tombent (confirmé par l'utilisateur, 2026-09-21).
    amelia, asporov = play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Stop Opp. Ability")

    assert (amelia.ability_fight, asporov.ability_fight) == (None, None)


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


def test_double_protection_versus_all_stop_is_a_cycle_where_the_stops_win(template_game):
    # Protection: Ability (bonus) + Protection: Bonus (ability) face à SoA + SoB : chaîne infinie, les Stops gagnent
    # (confirmé par l'utilisateur, 2026-09-21). Amelia n'a plus que Stop : son bonus -2 ne s'applique pas ; Asporov sans bonus.
    amelia, asporov = play(template_game, ally_ability="Stop Opp. Ability", ally_bonus="Stop Opp. Bonus",
                           enemy_ability="Protection: Bonus", enemy_bonus="Protection: Ability")

    assert (asporov.ability_fight, asporov.bonus_fight) == (None, None)
    assert (amelia.power_fight, asporov.power_fight) == (3, 7)


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
    amelia, asporov = play(template_game, ally_ability="Copy: Opp. Ability", enemy_ability="Stop Opp. Bonus")

    assert (amelia.power_fight, asporov.power_fight) == (3, 7)   # deux SoB en ability : les deux bonus tombent


def test_copied_stop_is_itself_subject_to_the_chain(template_game):
    _, asporov = play(template_game, ally_ability="Copy: Opp. Bonus", enemy_ability="Power +2", enemy_bonus="Stop Opp. Ability")

    assert asporov.power_fight == 7 + 2 - 2   # le SoA copié (ability) est stoppé par le SoA d'origine (bonus) : « Power +2 » tient


# --- Copy / Exchange de power et damage -------------------------------------------------------

def test_power_impose_gives_the_opponent_my_printed_power(template_game):
    # Règle officielle : « The opposing character has equal Power to your card. This number only takes into account the
    # figure shown on your card and does not include changes related to an Ability, Bonus or Fury. »
    _, asporov = play(template_game, ally_ability="Power Impose")

    assert asporov.power_fight == 3 - 2   # puissance imprimée d'Amelia (3), puis le bonus d'Amelia (-2)


def test_damage_impose_gives_the_opponent_my_printed_damage(template_game):
    _, asporov = play(template_game, ally_ability="Damage Impose")

    assert asporov.damage_fight == 5


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


# --- Cards : les deux cartes du round ---------------------------------------------------------

def test_minus_cards_damage_reduces_both_cards(template_game):
    amelia, asporov = play(template_game, ally_ability="-2 Cards Damage, Min 2")

    assert (amelia.damage_fight, asporov.damage_fight) == (5 - 2, max(2, 3 - 2))


def test_cards_damage_plus_raises_both_cards(template_game):
    amelia, asporov = play(template_game, ally_ability="Cards Damage +2")

    assert (amelia.damage_fight, asporov.damage_fight) == (7, 5)


def test_protection_cards_power_shields_both_cards_from_power_reductions(template_game):
    amelia, asporov = play(template_game, ally_ability="Protection: Cards Power And Damage", enemy_ability="-3 Opp Damage, Min 1")

    assert (amelia.power_fight, amelia.damage_fight, asporov.power_fight) == (3, 5, 7)   # les deux bonus -2 opp power et le -3 damage sont neutralisés


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


# --- Tune Out (bonus Cosmohnuts) : « the Attack calculation is ignored and the winner of the round is the player who
# bet the most Pillz. In case of a tie in Pillz, the two cards are decided in the same way as for a tie in Attack. » ---

def test_tune_out_makes_the_most_pillz_win_whatever_the_attack(template_game):
    amelia, asporov = play(template_game, ally_bonus="Tune Out", ally_pillz=2, enemy_pillz=1)   # sans Tune Out : 3 x 2 = 6 > 5 x 1... mais Asporov P7 : 7

    assert (amelia.attack, asporov.attack) == (2, 1)
    assert amelia.win is True


def test_tune_out_ties_on_pillz_fall_back_to_the_attack_tie_rule(template_game):
    amelia, asporov = play(template_game, ally_bonus="Tune Out", ally_pillz=1, enemy_pillz=1)   # Amelia 3 étoiles < Asporov 4

    assert amelia.win is True


def test_tune_out_applies_when_only_the_opponent_has_it(template_game):
    amelia, asporov = play(template_game, enemy_bonus="Tune Out", ally_pillz=3, enemy_pillz=2)   # Asporov aurait 7 x 2 = 14 > 3 x 3 = 9

    assert amelia.win is True


def test_tune_out_ignores_the_fury_pillz(template_game):
    # Confirmé par l'utilisateur (2026-09-21) : les 3 pillz de fury ne comptent pas dans la comparaison.
    amelia, asporov = template_game.ally.cards[AMELIA], template_game.enemy.cards[ASPOROV]
    amelia.ability, asporov.ability = None, None
    amelia.bonus, asporov.bonus = capacity("Tune Out"), capacity("-2 Opp Power, Min 1")
    process_round(template_game, ProcessRoundInput(player1_card_index=AMELIA, player1_pillz=2, player1_fury=True,
                                                   player2_card_index=ASPOROV, player2_pillz=3))

    assert (amelia.attack, asporov.attack) == (2, 3)
    assert asporov.win is True



# --- Par Pillz restante : glossaire officiel (66) : « le nombre de Pillz qu'il te reste avant de mettre des pillz sur ton
# perso (sans compter la Pillz gratuite) » — Lady Ametia Cr : 13 de puissance au round 1 ---------------------------

def test_per_pillz_left_counts_the_pillz_before_the_bet(template_game):
    amelia, _ = play(template_game, ally_ability="+1 Attack Per Pillz Left", ally_pillz=6)   # 12 pillz avant la mise de 5

    assert amelia.attack == 1 * 6 + 12


def test_per_pillz_left_ignores_the_fury_cost_too(template_game):
    amelia = template_game.ally.cards[AMELIA]
    amelia.ability = capacity("+1 Attack Per Pillz Left")
    amelia.bonus = capacity("-2 Opp Power, Min 1")
    template_game.enemy.cards[ASPOROV].ability = None
    process_round(template_game, ProcessRoundInput(player1_card_index=AMELIA, player1_pillz=2, player1_fury=True,
                                                   player2_card_index=ASPOROV, player2_pillz=1))

    assert amelia.attack == 1 * 2 + 12
