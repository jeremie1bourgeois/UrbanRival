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
from src.core.use_cases.process_round import check_capacity_condition, process_round
from src.schemas.game_schemas import ProcessRoundInput


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
    assert DEFERRED_CONDITIONS == {"stop", "killshot", "perfect", "defeat", "backlash", "victory_defeat"}


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


def test_versus_condition_looks_at_the_whole_opposing_hand_not_only_the_card_faced(template_game):
    # Règle officielle : « activates only if your opponent's hand has at least 1 card of a specific clan […]
    # your card's ability activates nonetheless, even if your card does not fight the card from the clan ».
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:Rescue"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True    # face à Asporov (All Stars), Serafina (Rescue) est dans la main


def test_versus_condition_fails_when_no_card_of_the_clan_is_in_the_opposing_hand(template_game):
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:Junkz"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is False


def test_versus_condition_for_the_enemy_side_looks_at_the_ally_hand(template_game):
    capacity = Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=["versus:Rescue"])

    assert check_capacity_condition(template_game, capacity, False, 3, 2) is False  # aucune Rescue chez l'allié


# --- Unison / Disunion : composition de la main (règle officielle : Unison = main EXCLUSIVEMENT du clan de la carte,
# Disunion = au moins une carte d'un autre clan) ---------------------------------------------------------------

def _hand_capacity(condition):
    return Capacity(target="ally", types=["power"], value=2, borne=-1, effect_conditions=[condition])


def test_unison_is_met_when_the_whole_hand_shares_the_card_clan(template_game):
    assert check_capacity_condition(template_game, _hand_capacity("unison"), True, 0, 0) is True    # 4 All Stars


def test_unison_fails_when_another_clan_is_in_the_hand(template_game):
    assert check_capacity_condition(template_game, _hand_capacity("unison"), False, 0, 2) is False  # Asporov : 3 All Stars + Serafina (Rescue)


def test_disunion_is_met_when_another_clan_is_in_the_hand(template_game):
    assert check_capacity_condition(template_game, _hand_capacity("disunion"), False, 0, 2) is True


def test_disunion_fails_on_a_mono_clan_hand(template_game):
    assert check_capacity_condition(template_game, _hand_capacity("disunion"), True, 0, 0) is False


# --- After (Clan X) : une carte du clan jouée par le même joueur au round précédent (règle officielle ; jamais au round 1) ---

def _play_round_one(game):
    process_round(game, ProcessRoundInput(player1_card_index=2, player1_pillz=1, player2_card_index=3, player2_pillz=1))   # Amelia (All Stars) vs Serafina (Rescue)


def test_after_is_never_met_on_the_first_round(template_game):
    assert check_capacity_condition(template_game, _hand_capacity("after:All Stars"), True, 0, 0) is False


def test_after_is_met_when_i_played_a_card_of_the_clan_last_round(template_game):
    _play_round_one(template_game)

    assert check_capacity_condition(template_game, _hand_capacity("after:All Stars|Tolvack"), True, 0, 0) is True     # Amelia
    assert check_capacity_condition(template_game, _hand_capacity("after:Rescue"), False, 0, 0) is True             # Serafina


def test_after_looks_at_my_own_previous_card_not_the_opponent_one(template_game):
    _play_round_one(template_game)

    assert check_capacity_condition(template_game, _hand_capacity("after:Rescue"), True, 0, 0) is False


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
