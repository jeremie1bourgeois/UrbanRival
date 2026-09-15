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
    template_game.ally.cards[0].pillz_fight = 2

    assert check_capacity_condition(template_game, _bet_capacity(3), True, 0, 0) is False


def test_bet_condition_is_met_when_enemy_bets_more_pillz_than_threshold(template_game):
    template_game.enemy.cards[1].pillz_fight = 5

    assert check_capacity_condition(template_game, _bet_capacity(3), False, 1, 0) is True
