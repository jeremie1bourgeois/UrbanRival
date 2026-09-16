"""
Niveau 3 : effets life/pillz après combat. Scénario de base : Amelia (allié, P3 D5, idx 2) contre
Asporov (ennemi, P7 D3, idx 0). Les abilities d'origine sont neutralisées (None) sauf celle passée en
paramètre ; bonus de clan -2 opp power actifs des deux côtés (4 et 3 All Stars) : Amelia 1 x pillz,
Asporov 5 x pillz. L'allié gagne avec 6 pillz contre 1 (6 > 5), perd avec 1 contre 2 (1 < 10).
Dégâts : Amelia 5, Asporov 3.
"""
import pytest

from src.core.domain.capacity import Capacity
from src.core.parsing.capacity_parser import parse_capacity
from src.core.services.game_service import check_end
from src.core.use_cases.apply_capacity_lvl_3 import apply_target_both_effects
from src.core.use_cases.process_round import process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput

AMELIA, ASPOROV, ASHLEY, SERAFINA = 2, 0, 3, 3


def ability(text):
    parsed = parse_capacity(text)
    assert parsed.supported, parsed.reason
    return parsed.capacity


def play(game, ally_index=AMELIA, enemy_index=ASPOROV, ally_wins=True, ally_ability=None, enemy_ability=None, ally_pillz=None, enemy_pillz=None):
    if ally_index == AMELIA:
        game.ally.cards[AMELIA].ability = ability(ally_ability) if ally_ability else None
    if enemy_index == ASPOROV:
        game.enemy.cards[ASPOROV].ability = ability(enemy_ability) if enemy_ability else None
    round_data = ProcessRoundInput(
        player1_card_index=ally_index, player1_pillz=ally_pillz if ally_pillz is not None else (6 if ally_wins else 1),
        player2_card_index=enemy_index, player2_pillz=enemy_pillz if enemy_pillz is not None else (1 if ally_wins else 2),
    )
    process_round(game, round_data)
    return game


def test_both_life_effect_without_bound_applies_to_both_players(template_game):
    ally, enemy = template_game.ally, template_game.enemy
    ally.life, enemy.life = 10, 8
    capacity = Capacity(target="both", types=["life"], value=2, borne=-1)

    apply_target_both_effects(template_game, ally, enemy, capacity, ally.cards[0], enemy.cards[0])

    assert (ally.life, enemy.life) == (12, 10)


# --- Application unique et symétrique ---------------------------------------------------------

def test_enemy_card_minus_opp_life_is_applied_once(template_game):
    play(template_game, ally_wins=False, enemy_ability="-2 Opp. Life, Min 0")

    assert template_game.ally.life == 12 - 3 - 2          # dégâts d'Asporov puis -2, pas -4


def test_enemy_card_plus_life_is_applied(template_game):
    play(template_game, ally_wins=False, enemy_ability="+2 Life")

    assert template_game.enemy.life == 14


def test_ally_card_plus_pillz_is_applied_once(template_game):
    play(template_game, ally_wins=True, ally_ability="+3 Pillz")

    assert template_game.ally.pillz == 12 - 5 + 3


def test_ally_card_minus_opp_pillz_respects_min(template_game):
    template_game.enemy.pillz = 3

    play(template_game, ally_wins=True, ally_ability="-4 Opp. Pillz, Min 2")

    assert template_game.enemy.pillz == 2


def test_life_per_opp_damage_multiplier(template_game):
    play(template_game, ally_wins=True, ally_ability="+1 Life Per Opp. Damage")   # Asporov : 3 dégâts

    assert template_game.ally.life == 12 + 3


# --- Conditions de fin de round ---------------------------------------------------------------

def test_unconditional_life_effect_only_applies_on_victory(template_game):
    play(template_game, ally_wins=False, ally_ability="+2 Life")

    assert template_game.ally.life == 12 - 3


def test_defeat_effect_only_applies_on_defeat(template_game):
    play(template_game, ally_wins=False, ally_ability="Defeat: +2 Life")

    assert template_game.ally.life == 12 - 3 + 2


def test_defeat_effect_does_not_apply_on_victory(template_game):
    play(template_game, ally_wins=True, ally_ability="Defeat: +2 Life")

    assert template_game.ally.life == 12


def test_backlash_hurts_the_winner_itself(template_game):
    play(template_game, ally_wins=True, ally_ability="Backlash: -2 Life Min 0")

    assert (template_game.ally.life, template_game.enemy.life) == (10, 7)


def test_backlash_does_nothing_on_defeat(template_game):
    play(template_game, ally_wins=False, ally_ability="Backlash: -2 Life Min 0")

    assert template_game.ally.life == 12 - 3


@pytest.mark.parametrize("ally_wins, expected_enemy_life", [(True, 12 - 5 - 2), (False, 12 - 2)])
def test_victory_or_defeat_applies_either_way(template_game, ally_wins, expected_enemy_life):
    play(template_game, ally_wins=ally_wins, ally_ability="Victory Or Defeat: -2 Opp. Life, Min 0")

    assert template_game.enemy.life == expected_enemy_life


# --- Reanimate --------------------------------------------------------------------------------

def test_reanimate_revives_the_owner_who_falls_to_zero(template_game):
    template_game.enemy.life = 3

    play(template_game, ally_index=AMELIA, enemy_index=SERAFINA, ally_pillz=6)   # Serafina perd, 5 dégâts -> 0

    assert template_game.enemy.life == 1                                        # Support x1 Rescue
    assert check_end(template_game) is GameResult.NONE


def test_reanimate_does_not_heal_on_victory(template_game):
    play(template_game, ally_index=ASHLEY, enemy_index=SERAFINA, ally_pillz=1, enemy_pillz=2)   # Serafina gagne

    assert template_game.enemy.life == 12


def test_reanimate_of_the_winner_does_not_fire_when_the_loser_dies(template_game):
    template_game.ally.life = 5

    play(template_game, ally_index=ASHLEY, enemy_index=SERAFINA, ally_pillz=1, enemy_pillz=2)   # Ashley perd, 5 dégâts -> 0

    assert (template_game.ally.life, template_game.enemy.life) == (0, 12)
    assert check_end(template_game) is GameResult.ENEMY


def test_end_of_round_effects_are_skipped_when_a_player_is_knocked_out(template_game):
    template_game.ally.life = 3

    play(template_game, ally_wins=False, ally_ability="Defeat: +2 Life")         # 3 dégâts -> 0, pas de rattrapage

    assert template_game.ally.life == 0


# --- Killshot : attaque >= 2 x attaque adverse ------------------------------------------------

def test_killshot_fires_when_attack_is_at_least_double(template_game):
    play(template_game, ally_ability="Killshot: +3 Life", ally_pillz=10, enemy_pillz=1)   # 10 >= 2 x 5

    assert template_game.ally.life == 15


def test_killshot_does_not_fire_on_a_narrower_victory(template_game):
    play(template_game, ally_ability="Killshot: +3 Life", ally_pillz=9, enemy_pillz=1)    # 9 > 5 mais < 10

    assert template_game.ally.life == 12


def test_killshot_gates_persistent_effects_too(template_game):
    play(template_game, ally_ability="Killshot: Toxin 1, Min 0", ally_pillz=9, enemy_pillz=1)

    assert template_game.enemy.effect_list == []


# --- Multiplicateur « per damage » ------------------------------------------------------------

def test_life_per_damage_counts_the_damage_inflicted(template_game):
    play(template_game, ally_wins=True, ally_ability="+1 Life Per Damage")   # Amelia inflige 5

    assert template_game.ally.life == 12 + 5


def test_life_per_damage_is_zero_on_defeat(template_game):
    play(template_game, ally_wins=False, ally_ability="Victory Or Defeat: +1 Life Per Damage")

    assert template_game.ally.life == 12 - 3


# --- Recover X Pillz Out Of Y ----------------------------------------------------------------

def test_defeat_recover_returns_part_of_the_pillz_bet(template_game):
    # Amelia mise 5 pillz (pillz_fight 6) et perd contre Asporov à 8 pillz : récupère floor(5 x 2 / 3) = 3
    play(template_game, ally_ability="Defeat: Recover 2 Pillz Out Of 3", ally_pillz=6, enemy_pillz=8)

    assert template_game.ally.cards[AMELIA].win is False
    assert template_game.ally.pillz == 12 - 5 + 3


def test_defeat_recover_counts_fury_pillz(template_game):
    amelia = template_game.ally.cards[AMELIA]
    amelia.ability = ability("Defeat: Recover 2 Pillz Out Of 3")
    process_round(template_game, ProcessRoundInput(player1_card_index=AMELIA, player1_pillz=3, player1_fury=True,
                                                   player2_card_index=ASPOROV, player2_pillz=8))   # 2 + 3 fury = 5 misées

    assert template_game.ally.pillz == 12 - 5 + 3


def test_defeat_recover_does_nothing_on_victory(template_game):
    play(template_game, ally_ability="Defeat: Recover 2 Pillz Out Of 3", ally_wins=True)   # 5 misées, victoire

    assert template_game.ally.pillz == 12 - 5


def test_unconditional_recover_applies_on_victory(template_game):
    play(template_game, ally_ability="Recover 1 Pillz Out Of 2", ally_wins=True)           # 5 misées -> 2

    assert template_game.ally.pillz == 12 - 5 + 2
