"""
L'API moteur pure (src/core/ai/engine_api.py) : c'est la fondation sur laquelle l'IA joue des milliers de
parties. La propriété qui compte vraiment est la première testée ici : `step` ne modifie pas l'état qu'on lui
donne. Sans elle, une IA qui explore un coup « pour voir » casserait la partie en cours.
"""
import copy

import pytest

from src.core.ai.engine_api import (STARTING_LIFE, is_terminal, legal_actions, new_game, step, winner)
from src.core.ai.opponent import Pick
from src.core.domain.game import NB_ROUNDS


@pytest.fixture
def game(template_game):
    return new_game(template_game.ally.cards, template_game.enemy.cards)


def _first_legal(state, side):
    return legal_actions(state, side)[0]


def test_step_leaves_the_given_state_untouched(game):
    before = copy.deepcopy(game.to_dict())

    step(game, Pick(0, 1, False), Pick(0, 1, False))

    assert game.to_dict() == before


def test_step_returns_a_state_that_advanced_one_round(game):
    after, result = step(game, Pick(0, 1, False), Pick(0, 1, False))

    assert after.nb_turn == game.nb_turn + 1
    assert len(after.history) == len(game.history) + 1
    assert result.done is False and result.winner is None


def test_a_fresh_game_is_not_finished_and_starts_at_full_life(game):
    assert not is_terminal(game)
    assert winner(game) is None
    assert (game.ally.life, game.enemy.life) == (STARTING_LIFE, STARTING_LIFE)


def test_new_game_copies_the_cards_so_two_games_do_not_share_them(template_game):
    first = new_game(template_game.ally.cards, template_game.enemy.cards)
    second = new_game(template_game.ally.cards, template_game.enemy.cards)

    step(first, Pick(0, 1, False), Pick(0, 1, False))

    # `played` vient du JSON du template, où il vaut 0 plutôt que false : on teste donc la valeur, pas le type.
    assert not second.ally.cards[0].played
    assert not template_game.ally.cards[0].played


def test_legal_actions_shrink_as_cards_are_played(game):
    before = legal_actions(game, "ally")
    after_state, _ = step(game, Pick(0, 1, False), Pick(0, 1, False))
    after = legal_actions(after_state, "ally")

    assert {pick.card_index for pick in before} == {0, 1, 2, 3}
    assert 0 not in {pick.card_index for pick in after}


def test_legal_actions_never_bet_more_pillz_than_available(game):
    game.ally.pillz = 2

    for pick in legal_actions(game, "ally"):
        spent = (pick.pillz - 1) + (3 if pick.fury else 0)
        assert spent <= game.ally.pillz


def test_a_finished_game_offers_no_action_and_refuses_another_round(game):
    state = game
    while not is_terminal(state):
        state, _ = step(state, _first_legal(state, "ally"), _first_legal(state, "enemy"))

    assert legal_actions(state, "ally") == []
    with pytest.raises(ValueError, match="already finished"):
        step(state, Pick(0, 1, False), Pick(0, 1, False))


def test_a_game_ends_after_four_rounds_at_the_latest(game):
    state, rounds = game, 0
    while not is_terminal(state):
        state, _ = step(state, _first_legal(state, "ally"), _first_legal(state, "enemy"))
        rounds += 1

    assert rounds <= NB_ROUNDS
    assert winner(state) in ("ally", "enemy", "draw")


def test_the_player_left_with_more_life_wins(game):
    game.ally.life, game.enemy.life = 7, 3
    game.nb_turn = NB_ROUNDS + 1

    assert winner(game) == "ally"


def test_a_player_at_zero_life_loses_whatever_the_round(game):
    game.enemy.life = 0

    assert is_terminal(game)
    assert winner(game) == "ally"


def test_reward_is_plus_one_for_an_ally_win_and_minus_one_for_a_loss(game):
    game.nb_turn = NB_ROUNDS          # dernier round
    game.ally.life, game.enemy.life = 10, 1

    _, result = step(game, Pick(0, 12, False), Pick(0, 1, False))

    assert result.done is True
    assert result.reward == pytest.approx(1.0 if result.winner == "ally" else -1.0 if result.winner == "enemy" else 0.0)
    assert result.life_gap == result.life["ally"] - result.life["enemy"]


def test_unknown_side_is_rejected(game):
    with pytest.raises(ValueError, match="Unknown side"):
        legal_actions(game, "nobody")
