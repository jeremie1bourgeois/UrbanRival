"""
Niveau 4 : effets persistants (poison / toxin / heal / regen / dope). Toutes les abilities du template sont
neutralisées ; bonus de clan -2 opp power (celui de Serafina est inactif). À 1 pillz chacun :
  R1 Amelia (1) vs Asporov (5)  : Asporov gagne, allié -3    | Amelia gagne avec 6 pillz (6 > 5) : ennemi -5
  R2 Allison (3) vs Bhudd (2)   : Allison gagne, ennemi -3   | Bhudd gagne avec 2 pillz (4 > 3) : allié -2
  R3 Agustino (4) vs B Mappe (1): Agustino gagne, ennemi -2  | B Mappe gagne avec 5 pillz (5 > 4) : allié -8
  R4 Ashley (5) vs Serafina (6) : Serafina gagne, allié -8   | Ashley gagne avec 2 pillz (10 > 6) : ennemi -1
"""
import pytest

from src.core.domain.game import Game
from src.core.parsing.capacity_parser import parse_capacity
from src.core.services.game_service import check_end
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput

ROUNDS = [(2, 0), (1, 2), (0, 1), (3, 3)]   # (index allié, index ennemi) des rounds 1 à 4


@pytest.fixture
def game(template_game):
    for player in (template_game.ally, template_game.enemy):
        for card in player.cards:
            card.ability = None
    return template_game


def ability(text):
    parsed = parse_capacity(text)
    assert parsed.supported, parsed.reason
    return parsed.capacity


def play(game, round_number, ally_ability=None, enemy_ability=None, ally_pillz=1, enemy_pillz=1):
    ally_index, enemy_index = ROUNDS[round_number - 1]
    if ally_ability:
        game.ally.cards[ally_index].ability = ability(ally_ability)
    if enemy_ability:
        game.enemy.cards[enemy_index].ability = ability(enemy_ability)
    round_data = ProcessRoundInput(player1_card_index=ally_index, player1_pillz=ally_pillz,
                                   player2_card_index=enemy_index, player2_pillz=enemy_pillz)
    check_round_correct(game, round_data)
    process_round(game, round_data)


def effects(player):
    return [(effect.kind, effect.value, effect.borne) for effect in player.effect_list]


# --- Activation -------------------------------------------------------------------------------

def test_poison_is_registered_on_the_opponent_when_the_card_wins(game):
    play(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)

    assert (effects(game.enemy), effects(game.ally)) == ([("poison", 2, 1)], [])


def test_poison_is_not_registered_when_the_card_loses(game):
    play(game, 1, ally_ability="Poison 2, Min 1")

    assert effects(game.enemy) == []


def test_defeat_poison_is_registered_when_the_card_loses(game):
    play(game, 1, ally_ability="Defeat: Poison 2, Min 1")

    assert effects(game.enemy) == [("poison", 2, 1)]


def test_backlash_poison_poisons_the_owner(game):
    play(game, 1, ally_ability="Backlash: Poison 1, Min 0", ally_pillz=6)

    assert (effects(game.ally), effects(game.enemy)) == ([("poison", 1, 0)], [])


def test_multiplier_is_resolved_at_activation(game):
    play(game, 1)
    play(game, 2, ally_ability="Growth: Poison 1, Min 0")   # round 2 : x2

    assert effects(game.enemy) == [("poison", 2, 0)]


def test_persistent_capacity_is_consumed(game):
    play(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)

    assert game.ally.cards[2].ability_fight is None


# --- Tick -------------------------------------------------------------------------------------

def test_poison_does_not_tick_on_the_activation_round(game):
    play(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)

    assert game.enemy.life == 12 - 5


def test_poison_ticks_at_the_end_of_each_following_round(game):
    play(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)   # ennemi 7

    play(game, 2, enemy_pillz=2)                                   # Bhudd gagne : ennemi 7, puis poison -> 5
    assert game.enemy.life == 5
    play(game, 3, enemy_pillz=5)                                   # B Mappe gagne : ennemi 5, puis poison -> 3
    assert game.enemy.life == 3


def test_poison_respects_its_minimum(game):
    game.enemy.life = 8
    play(game, 1, ally_ability="Poison 2, Min 2", ally_pillz=6)   # ennemi 3

    play(game, 2, enemy_pillz=2)
    assert game.enemy.life == 2                                    # 3 -> max(2, 1)
    play(game, 3, enemy_pillz=5)
    assert game.enemy.life == 2                                    # déjà au minimum : rien


def test_poison_can_knock_out(game):
    game.enemy.life = 8
    play(game, 1, ally_ability="Poison 3, Min 0", ally_pillz=6)   # ennemi 3

    play(game, 2, enemy_pillz=2)                                   # Bhudd gagne, puis poison : 3 -> 0

    assert (game.enemy.life, check_end(game)) == (0, GameResult.ALLY)


def test_heal_ticks_for_the_owner_up_to_its_maximum(game):
    game.ally.life = 4
    play(game, 1, ally_ability="Heal 3 Max. 9", ally_pillz=6)

    play(game, 2, enemy_pillz=2)                                   # Bhudd gagne : allié 4 - 2 = 2, puis heal -> 5
    assert game.ally.life == 5
    play(game, 3)                                                  # Agustino gagne : allié 5, heal -> 8
    assert game.ally.life == 8
    play(game, 4, ally_pillz=2)                                    # Ashley gagne : 8 + 3 -> plafonné à 9
    assert game.ally.life == 9


def test_dope_adds_pillz_up_to_its_maximum(game):
    play(game, 1, ally_ability="Dope 2, Max. 10", ally_pillz=6)   # allié 12 - 5 = 7 pillz

    play(game, 2)
    assert game.ally.pillz == 9
    play(game, 3)
    assert game.ally.pillz == 10


# --- Remplacement et cumul --------------------------------------------------------------------

def test_a_new_poison_replaces_the_previous_one_after_it_ticked(game):
    play(game, 1, ally_ability="Poison 1, Min 0", ally_pillz=6)   # ennemi 7

    play(game, 2, ally_ability="Poison 3, Min 0")                  # Allison gagne : 7 - 3 = 4, ancien poison -> 3

    assert (game.enemy.life, effects(game.enemy)) == (3, [("poison", 3, 0)])


def test_toxin_stacks_with_poison(game):
    game.enemy.life = 14
    play(game, 1, ally_ability="Poison 1, Min 0", ally_pillz=6)   # ennemi 9
    play(game, 2, ally_ability="Toxin 2, Min 0")                   # Allison gagne : 9 - 3 = 6, poison -> 5

    play(game, 3, enemy_pillz=5)                                   # B Mappe gagne : 5 - 1 - 2 -> 2

    assert (game.enemy.life, effects(game.enemy)) == (2, [("poison", 1, 0), ("toxine", 2, 0)])


def test_regen_stacks_with_heal_and_a_new_heal_replaces_the_old_one(game):
    game.ally.life = 4
    play(game, 1, ally_ability="Heal 1 Max. 12", ally_pillz=6)
    play(game, 2, ally_ability="Regen 2, Max. 12")                 # heal -> 5
    play(game, 3, ally_ability="Heal 3 Max. 12")                   # heal 1 + regen 2 -> 8, puis heal 3 remplace heal 1

    play(game, 4, ally_pillz=2)                                    # regen 2 + heal 3 -> 13 -> plafonné 12

    assert game.ally.life == 12
    assert sorted(effects(game.ally)) == [("heal", 3, 12), ("regen", 2, 12)]


# --- Sérialisation ----------------------------------------------------------------------------

def test_persistent_effects_survive_a_json_round_trip(game):
    play(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)

    restored = Game.from_dict_template(game.to_dict())

    assert effects(restored.enemy) == [("poison", 2, 1)]
    assert restored.to_dict() == game.to_dict()


def test_repair_adds_pillz_and_stacks_with_dope(game):
    play(game, 1, ally_ability="Dope 1, Max. 12", ally_pillz=6)     # allié 7 pillz
    play(game, 2, ally_ability="Repair 2, Max. 12")                  # dope -> 8

    play(game, 3)                                                    # dope 1 + repair 2 -> 11

    assert (game.ally.pillz, sorted(effects(game.ally))) == (11, [("dope", 1, 12), ("repair", 2, 12)])
