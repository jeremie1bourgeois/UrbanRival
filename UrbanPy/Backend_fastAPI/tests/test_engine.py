"""
Tests du moteur pur (process_round) sur les cartes du template, sans HTTP ni disque.

Rappel du template : nb_turn = 1, turn = False (l'ennemi joue en premier), 12 vies / 12 pillz.
  Allié  : 0 Agustino 2★ P6 D2 (Growth: -1 Opp Power, Min 4) | 1 Allison 3★ P5 D3 (Courage: Damage +3)
           2 Amelia 3★ P3 D5 (Power +4)                      | 3 Ashley 2★ P5 D1 (-3 Opp Damage, Min 2)
           bonus All Stars : -2 Opp Power, Min 1
  Ennemi : 0 Asporov 4★ P7 D3 (Support: Damage +1)          | 1 B Mappe Mt 5★ P3 D8 (Equalizer: -1 Opp Pow & Dam, Min 1)
           2 Bhudd 3★ P4 D2 (Stop Opp. Bonus)                | 3 Serafina (Rescue) 5★ P8 D8 (Support: Reanimate +1 Life ; bonus Support: Attack +3)
Les pillz d'un round valent 1 au minimum (= aucune pillz ajoutée) : attaque = puissance x pillz, coût = pillz - 1 (+3 en fury).
"""
import pytest

from src.core.services.game_service import check_end
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput

AGUSTINO, ALLISON, AMELIA, ASHLEY = 0, 1, 2, 3
ASPOROV, B_MAPPE, BHUDD, SERAFINA = 0, 1, 2, 3


def play(game, ally_index, enemy_index, ally_pillz=1, enemy_pillz=1, ally_fury=False, enemy_fury=False):
    round_data = ProcessRoundInput(
        player1_card_index=ally_index, player1_pillz=ally_pillz, player1_fury=ally_fury,
        player2_card_index=enemy_index, player2_pillz=enemy_pillz, player2_fury=enemy_fury,
    )
    check_round_correct(game, round_data)
    process_round(game, round_data)
    return game.ally.cards[ally_index], game.enemy.cards[enemy_index]


# --- Déroulement d'un round -------------------------------------------------------------------

def test_round_consumes_added_pillz_and_advances_the_game(template_game):
    play(template_game, AMELIA, BHUDD, ally_pillz=3, enemy_pillz=2)

    assert (template_game.ally.pillz, template_game.enemy.pillz) == (10, 11)
    assert (template_game.nb_turn, template_game.turn) == (2, True)


def test_round_is_recorded_in_history_and_on_the_cards(template_game):
    amelia, bhudd = play(template_game, AMELIA, BHUDD, ally_pillz=3, enemy_pillz=3)

    (round_played,) = template_game.history
    assert (round_played.ally.card_index, round_played.enemy.card_index) == (AMELIA, BHUDD)
    assert (round_played.ally.win, round_played.enemy.win) == (True, False)
    assert (amelia.played, amelia.win, bhudd.played, bhudd.win) == (True, True, True, False)


def test_attack_is_fight_power_times_pillz_and_loser_takes_fight_damage(template_game):
    amelia, bhudd = play(template_game, AMELIA, BHUDD, ally_pillz=3, enemy_pillz=3)

    assert (amelia.power_fight, amelia.attack) == (5, 15)
    assert (bhudd.power_fight, bhudd.attack) == (4, 12)
    assert (template_game.ally.life, template_game.enemy.life) == (12, 7)


# --- Bonus et abilities de niveau 2 (power / damage / attack) ---------------------------------

def test_clan_bonus_minus_two_opp_power_applies_to_both_cards(template_game):
    allison, asporov = play(template_game, ALLISON, ASPOROV)

    assert (allison.power_fight, asporov.power_fight) == (3, 5)


def test_flat_power_ability_is_added_before_opponent_bonus(template_game):
    amelia, _ = play(template_game, AMELIA, ASPOROV)

    assert amelia.power_fight == 3 + 4 - 2


def test_stop_opp_bonus_cancels_only_the_opponent_bonus(template_game):
    amelia, bhudd = play(template_game, AMELIA, BHUDD)

    assert bhudd.power_fight == 4      # le bonus d'Amelia (-2) est stoppé
    assert amelia.power_fight == 5     # le bonus de Bhudd s'applique toujours


def test_minus_opp_damage_ability_respects_its_minimum(template_game):
    _, serafina = play(template_game, ASHLEY, SERAFINA)

    assert serafina.damage_fight == 5  # 8 - 3, min 2


def test_support_counts_every_card_of_the_clan_in_hand(template_game):
    _, asporov = play(template_game, ALLISON, ASPOROV)

    assert asporov.damage_fight == 3 + 1 * 3  # Asporov, B Mappe, Bhudd sont All Stars


# --- Activation du bonus de clan (>= 2 cartes du clan en main) --------------------------------

def test_clan_bonus_is_inactive_when_the_card_is_alone_in_its_clan(template_game):
    _, serafina = play(template_game, ASHLEY, SERAFINA, enemy_pillz=2)   # Serafina : seule Rescue de la main

    assert serafina.attack == (8 - 2) * 2                                # pas de "Support: Attack +3"


def test_clan_bonus_is_active_with_two_cards_of_the_clan_in_hand(template_game):
    template_game.enemy.cards[0].faction = "Rescue"                       # Asporov devient Rescue (jamais joué ici)

    _, serafina = play(template_game, ASHLEY, SERAFINA, enemy_pillz=2)

    assert serafina.attack == (8 - 2) * 2 + 3 * 2                        # support compte les 2 Rescue


def test_clan_bonus_counts_already_played_clan_mates(template_game):
    template_game.enemy.cards[0].faction = "Rescue"
    play(template_game, AGUSTINO, ASPOROV)                                # le second Rescue est joué au round 1

    _, serafina = play(template_game, ASHLEY, SERAFINA, enemy_pillz=2)

    assert serafina.attack == (8 - 2) * 2 + 3 * 2                        # la main reste la référence, pas les cartes en jeu


def test_equalizer_scales_with_opponent_stars_and_respects_its_minimum(template_game):
    agustino, _ = play(template_game, AGUSTINO, B_MAPPE)

    assert agustino.power_fight == 6 - 2 - 2   # equalizer x 2★ puis bonus -2
    assert agustino.damage_fight == 1          # 2 - 2, min 1


def test_growth_scales_with_the_round_number(template_game):
    template_game.nb_turn = 2

    _, asporov = play(template_game, AGUSTINO, ASPOROV)

    assert asporov.power_fight == 7 - 1 * 2 - 2  # growth x round 2 puis bonus -2


def test_growth_respects_its_minimum_before_the_bonus(template_game):
    template_game.nb_turn = 4

    _, asporov = play(template_game, AGUSTINO, ASPOROV)

    assert asporov.power_fight == 4 - 2  # 7 - 4 = 3 -> min 4, puis bonus -2


# --- Conditions de déclenchement --------------------------------------------------------------

def test_courage_triggers_when_the_player_plays_first(template_game):
    template_game.turn = True

    allison, _ = play(template_game, ALLISON, ASPOROV)

    assert allison.damage_fight == 3 + 3


def test_courage_does_not_trigger_when_the_player_plays_second(template_game):
    template_game.turn = False

    allison, _ = play(template_game, ALLISON, ASPOROV)

    assert allison.damage_fight == 3


# --- Fury -------------------------------------------------------------------------------------

def test_fury_adds_two_damage_and_costs_three_pillz(template_game):
    ashley, _ = play(template_game, ASHLEY, BHUDD, ally_pillz=2, ally_fury=True)

    assert ashley.damage_fight == 1 + 2
    assert template_game.ally.pillz == 12 - 1 - 3


# --- Égalités ---------------------------------------------------------------------------------

def test_tie_on_attack_is_won_by_the_card_with_fewer_stars(template_game):
    # Ashley 2★ : (5 - 2) x 5 = 15 ; Asporov 4★ : (7 - 2) x 3 = 15
    ashley, asporov = play(template_game, ASHLEY, ASPOROV, ally_pillz=5, enemy_pillz=3)

    assert (ashley.attack, asporov.attack) == (15, 15)
    assert (ashley.win, template_game.enemy.life) == (True, 11)


def test_tie_on_attack_and_stars_is_won_by_the_enemy_when_he_plays_first(template_game):
    # Allison 3★ : (5 - 2) x 4 = 12 ; Bhudd 3★ (stoppe le bonus adverse) : 4 x 3 = 12
    template_game.turn = False

    allison, bhudd = play(template_game, ALLISON, BHUDD, ally_pillz=4, enemy_pillz=3)

    assert (allison.attack, bhudd.attack) == (12, 12)
    assert (bhudd.win, template_game.ally.life) == (True, 10)


def test_tie_on_attack_and_stars_is_won_by_the_ally_when_he_plays_first(template_game):
    template_game.turn = True

    allison, bhudd = play(template_game, ALLISON, BHUDD, ally_pillz=4, enemy_pillz=3)

    assert (allison.attack, bhudd.attack) == (12, 12)
    assert (allison.win, template_game.enemy.life) == (True, 12 - (3 + 3))  # courage : Damage +3


# --- Validation d'un round --------------------------------------------------------------------

def test_refuses_more_pillz_than_the_player_owns(template_game):
    template_game.ally.pillz = 2

    with pytest.raises(ValueError, match="too many pillz"):
        play(template_game, AMELIA, BHUDD, ally_pillz=4)


def test_fury_counts_as_three_pillz_in_the_validation(template_game):
    template_game.ally.pillz = 2

    with pytest.raises(ValueError, match="too many pillz"):
        play(template_game, AMELIA, BHUDD, ally_pillz=1, ally_fury=True)


def test_refuses_a_card_already_played(template_game):
    play(template_game, AMELIA, BHUDD)

    with pytest.raises(ValueError, match="already played"):
        play(template_game, AMELIA, ASPOROV)


def test_refuses_an_out_of_range_card_index(template_game):
    with pytest.raises(ValueError, match="invalid card index"):
        play(template_game, 4, BHUDD)


# --- Partie complète --------------------------------------------------------------------------

def test_full_game_life_trajectory_and_final_result(template_game):
    trajectory = []
    for ally_index, enemy_index, fury in ((AMELIA, BHUDD, False), (ALLISON, ASPOROV, False), (AGUSTINO, B_MAPPE, False), (ASHLEY, SERAFINA, True)):
        play(template_game, ally_index, enemy_index, ally_pillz=2, enemy_pillz=2, ally_fury=fury, enemy_fury=fury)
        trajectory.append((template_game.ally.life, template_game.enemy.life))

    # R1 Amelia 10 > Bhudd 8 : -5 | R2 Allison 6 < Asporov 10 : -6 | R3 Agustino 4 > B Mappe 2 : -1
    # R4 Ashley 5x2 = 10 < Serafina 6x2 = 12 (bonus inactif : seule Rescue), dégâts (8 - 3) + 2 fury = 7 -> allié à 0
    assert [(ally, enemy) for ally, enemy in trajectory[:3]] == [(12, 7), (6, 7), (6, 6)]
    assert trajectory[3][0] == 0
    assert check_end(template_game) is GameResult.ENEMY


# --- Modificateurs d'attaque : après le calcul puissance x pillz ------------------------------

def test_minus_opp_attack_applies_to_the_computed_attack(template_game):
    from src.core.parsing.capacity_parser import parse_capacity
    template_game.enemy.cards[ASPOROV].ability = parse_capacity("-4 Opp Attack, Min 2").capacity

    amelia, _ = play(template_game, AMELIA, ASPOROV)   # Amelia (3 + 4 - 2) x 1 = 5, puis -4 min 2

    assert amelia.attack == 2


def test_attack_bonus_then_opp_attack_malus(template_game):
    from src.core.parsing.capacity_parser import parse_capacity
    template_game.ally.cards[AMELIA].ability = parse_capacity("Attack +6").capacity
    template_game.enemy.cards[ASPOROV].ability = parse_capacity("-4 Opp Attack, Min 0").capacity

    amelia, _ = play(template_game, AMELIA, ASPOROV, ally_pillz=2)   # (3 - 2) x 2 = 2, +6 = 8, -4 = 4

    assert amelia.attack == 4
