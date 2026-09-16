"""
Adversaires qui simulent un coup d'avance (glouton, minimax) et l'évaluation qu'ils maximisent.
Les tests bornent le budget de simulation pour rester rapides ; les vrais taux de victoire se mesurent avec
`scripts/ai_arena.py`.
"""
import functools
import random
import statistics

import pytest

from src.core.ai import arena, engine
from src.core.ai.engine import Pick
from src.core.ai.evaluation import LIFE_WEIGHT, WIN_SCORE, evaluate, hand_value
from src.core.ai.opponent import STRATEGIES, greedy_pick, minimax_pick, search_pick
from src.core.domain.game import NB_ROUNDS

# Budget réduit : ces tests vérifient le comportement, pas la force de jeu.
fast_greedy = functools.partial(search_pick, aggregate=statistics.fmean, max_candidates=12, nb_replies=3)
fast_minimax = functools.partial(search_pick, aggregate=min, max_candidates=12, nb_replies=3)


def test_evaluation_is_symmetric_between_the_two_sides(template_game):
    template_game.ally.life, template_game.enemy.life = 9, 4
    template_game.ally.pillz, template_game.enemy.pillz = 2, 7

    assert evaluate(template_game, "ally") == -evaluate(template_game, "enemy")


def test_evaluation_prefers_life_then_pillz_then_cards_in_hand(template_game):
    reference = evaluate(template_game, "ally")

    template_game.enemy.life -= 1
    with_one_life_ahead = evaluate(template_game, "ally")
    template_game.enemy.pillz -= 1
    with_pillz_too = evaluate(template_game, "ally")

    assert with_one_life_ahead == reference + LIFE_WEIGHT
    assert with_pillz_too > with_one_life_ahead
    assert with_one_life_ahead - reference > with_pillz_too - with_one_life_ahead   # la vie pèse plus


def test_a_won_game_outweighs_any_material_advantage(template_game):
    template_game.nb_turn = NB_ROUNDS + 1
    template_game.ally.life, template_game.enemy.life = 1, 0

    assert evaluate(template_game, "ally") == WIN_SCORE
    assert evaluate(template_game, "enemy") == -WIN_SCORE


def test_hand_value_only_counts_cards_left_to_play(template_game):
    before = hand_value(template_game.ally)
    played = template_game.ally.cards[0]
    played.played = True

    assert hand_value(template_game.ally) == before - (played.power + played.damage)


@pytest.mark.parametrize("strategy", [fast_greedy, fast_minimax])
def test_search_returns_a_legal_pick_on_every_round_of_a_game(template_game, strategy):
    rng = random.Random(3)
    state = template_game
    while not engine.is_terminal(state):
        ally = strategy(state, "ally", rng)
        enemy = strategy(state, "enemy", rng)
        assert ally in engine.legal_actions(state, "ally")
        assert enemy in engine.legal_actions(state, "enemy")
        state, _ = engine.step(state, ally, enemy)
    assert state.nb_turn > NB_ROUNDS or 0 in (state.ally.life, state.enemy.life)


def test_search_takes_the_winning_last_round_when_one_exists(template_game):
    """Dernier round, l'allié gagne s'il remporte le round : la recherche mise ce qu'il faut pour l'emporter."""
    state = _last_round(template_game, ally_life=1, enemy_life=2, ally_pillz=8, enemy_pillz=0, enemy_card=0)

    pick = fast_greedy(state, "ally", random.Random(0))

    after, _ = engine.step(state, pick, Pick(0, 1))
    assert after.enemy.life <= 0 or after.enemy.life < after.ally.life


def test_search_does_not_burn_pillz_it_does_not_need(template_game):
    """À avantage égal entre deux coups, la recherche garde ses pillz (départage sur la mise)."""
    state = _last_round(template_game, ally_life=12, enemy_life=1, ally_pillz=11, enemy_pillz=0)

    pick = fast_greedy(state, "ally", random.Random(0))

    assert pick.pillz - 1 < state.ally.pillz


def test_strategies_registry_exposes_the_four_opponents():
    assert sorted(STRATEGIES) == ["greedy", "heuristic", "minimax", "random"]
    assert STRATEGIES["greedy"] is greedy_pick and STRATEGIES["minimax"] is minimax_pick


def test_a_duel_plays_the_requested_number_of_games_and_swaps_sides():
    rng = random.Random(11)
    hands = arena.mirrored_hands(rng)

    result = arena.duel(STRATEGIES["random"], STRATEGIES["random"], nb_games=6, rng=rng,
                        hands_factory=lambda _: hands)

    assert result.games == 6
    assert 0.0 <= result.win_rate <= 1.0


def test_greedy_beats_random_over_a_handful_of_games():
    rng = random.Random(5)
    hands = arena.mirrored_hands(rng)

    result = arena.duel(fast_greedy, STRATEGIES["random"], nb_games=8, rng=rng, hands_factory=lambda _: hands)

    assert result.win_rate > 0.5, f"glouton contre aléatoire : {result}"


def test_random_hands_are_playable_and_span_two_clans():
    hand = arena.random_hand(random.Random(1))

    assert len(hand) == arena.CARDS_PER_HAND
    game = engine.new_game(hand, hand)
    assert len({card.faction for card in game.ally.cards}) == 2
    assert engine.legal_actions(game, "ally")


def _last_round(game, ally_life, enemy_life, ally_pillz, enemy_pillz, ally_card=3, enemy_card=3):
    """Partie au quatrième round : il ne reste qu'une carte à chaque joueur."""
    game.nb_turn = NB_ROUNDS
    game.ally.life, game.enemy.life = ally_life, enemy_life
    game.ally.pillz, game.enemy.pillz = ally_pillz, enemy_pillz
    for index in range(len(game.ally.cards)):
        game.ally.cards[index].played = index != ally_card
        game.enemy.cards[index].played = index != enemy_card
    return game
