from src.core.domain.round import Round
from src.core.use_cases.process_round import resolve_combat


def _fight_data(card, attack, damage):
    card.attack = attack
    card.damage_fight = damage


def test_tie_on_enemy_turn_reduces_ally_life_without_going_negative(template_game):
    # Égalité parfaite (même attaque, même nb d'étoiles) et ce n'est pas le tour de l'allié :
    # l'ennemi gagne et inflige ses dégâts, la vie doit rester >= 0.
    ally_card = template_game.ally.cards[1]    # Allison, 3 étoiles
    enemy_card = template_game.enemy.cards[2]  # Bhudd, 3 étoiles
    _fight_data(ally_card, attack=10, damage=3)
    _fight_data(enemy_card, attack=10, damage=3)
    template_game.turn = False
    template_game.ally.life = 12

    resolve_combat(template_game, ally_card, enemy_card, Round())

    assert enemy_card.win is True
    assert template_game.ally.life == 9


from src.core.domain.capacity import Capacity
from src.core.use_cases.process_round import check_capacity_condition


def _bet_capacity(threshold: int) -> Capacity:
    return Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=[f"bet {threshold}"])


def test_bet_condition_is_met_when_ally_bets_more_pillz_than_threshold(template_game):
    template_game.ally.cards[0].pillz_fight = 5

    assert check_capacity_condition(template_game, _bet_capacity(3), True, 0, 0) is True


def test_bet_condition_is_not_met_when_ally_bets_too_few_pillz(template_game):
    template_game.ally.cards[0].pillz_fight = 3

    assert check_capacity_condition(template_game, _bet_capacity(3), True, 0, 0) is False


def test_bet_condition_is_met_when_enemy_bets_more_pillz_than_threshold(template_game):
    template_game.enemy.cards[1].pillz_fight = 5

    assert check_capacity_condition(template_game, _bet_capacity(3), False, 1, 0) is True


import pytest

from src.core.use_cases.process_round import DEFERRED_CONDITIONS, process_round
from src.schemas.game_schemas import ProcessRoundInput


def test_none_capacity_has_no_condition_to_check(template_game):
    assert check_capacity_condition(template_game, None, True, 0, 0) is True


def test_deferred_condition_is_left_for_level_3(template_game):
    capacity = Capacity(target="enemy", types=["life"], value=-2, borne=0, effect_conditions=["defeat"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True
    assert capacity.effect_conditions == ["defeat"]


def test_met_condition_is_consumed_and_deferred_one_kept(template_game):
    template_game.turn = True
    capacity = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["courage", "defeat"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True
    assert capacity.effect_conditions == ["defeat"]


def test_unknown_condition_raises(template_game):
    capacity = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["moonlight"])

    with pytest.raises(ValueError, match="Invalid effect_conditions"):
        check_capacity_condition(template_game, capacity, True, 0, 0)


def test_deferred_conditions_constant():
    assert DEFERRED_CONDITIONS == {"stop", "killshot", "defeat", "backlash", "victory_defeat"}


def test_courage_life_ability_applies_and_leaves_the_original_untouched(template_game):
    # Allison reçoit "Courage: +2 Life" (capacité de niveau 3 avec condition de début de round)
    template_game.turn = True
    allison = template_game.ally.cards[1]
    allison.ability = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["courage"])
    round_data = ProcessRoundInput(player1_card_index=1, player1_pillz=4, player2_card_index=2, player2_pillz=1)

    process_round(template_game, round_data)   # Allison (5-2)x4 = 12 > Bhudd 4x1 = 4 : victoire

    assert allison.win is True
    assert template_game.ally.life == 14
    assert allison.ability.effect_conditions == ["courage"]


def test_versus_condition_is_met_against_a_listed_clan(template_game):
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:All Stars|Rescue"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True   # Asporov : All Stars
    assert capacity.effect_conditions == []


def test_versus_condition_fails_against_another_clan(template_game):
    template_game.enemy.cards[0].faction = "Junkz"
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:All Stars"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is False


def test_versus_condition_for_the_enemy_side_looks_at_the_ally_card(template_game):
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:Rescue"])

    assert check_capacity_condition(template_game, capacity, False, 3, 2) is False  # Amelia (All Stars) n'est pas Rescue


@pytest.mark.parametrize("condition, pillz_fight, expected", [
    # Règle officielle (texte des cartes Bet) : « including free Pillz and excluding Fury » -> on compare pillz_fight.
    ("bet>3", 4, True),    # 4 pillz au total (dont la gratuite) : strictement plus que 3
    ("bet>3", 3, False),   # 3 : pas strictement plus
    ("bet<6", 5, True),
    ("bet<6", 6, False),
    ("bet 3", 4, True),    # forme historique = « bet > 3 »
])
def test_bet_conditions_compare_the_pillz_actually_bet(template_game, condition, pillz_fight, expected):
    template_game.ally.cards[0].pillz_fight = pillz_fight
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=[condition])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is expected
