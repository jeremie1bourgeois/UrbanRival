from src.core.domain.capacity import Capacity
from src.core.use_cases.apply_capacity_lvl_3 import apply_target_both_effects


def test_both_life_effect_without_bound_applies_to_both_players(template_game):
    ally, enemy = template_game.ally, template_game.enemy
    ally.life, enemy.life = 10, 8
    capacity = Capacity(target="both", types=["life"], value=2, borne=-1)

    apply_target_both_effects(template_game, ally, enemy, capacity, ally.cards[0], enemy.cards[0])

    assert (ally.life, enemy.life) == (12, 10)
