import pytest

from src.core.services.game_service import check_end
from src.core.use_cases.process_round import check_round_correct
from src.schemas.game_schemas import GameResult, ProcessRoundInput


def _round_input() -> ProcessRoundInput:
    return ProcessRoundInput(player1_card_index=0, player1_pillz=1, player2_card_index=0, player2_pillz=1)


def test_game_is_not_over_while_fourth_round_remains_to_be_played(template_game):
    template_game.nb_turn = 4  # 3 rounds joués, le 4e est en cours
    template_game.ally.life, template_game.enemy.life = 12, 10

    assert check_end(template_game) is GameResult.NONE


def test_game_is_decided_on_life_once_four_rounds_are_played(template_game):
    template_game.nb_turn = 5
    template_game.ally.life, template_game.enemy.life = 12, 10

    assert check_end(template_game) is GameResult.ALLY


def test_fourth_round_is_accepted(template_game):
    template_game.nb_turn = 4

    check_round_correct(template_game, _round_input())  # ne doit pas lever


def test_fifth_round_is_refused(template_game):
    template_game.nb_turn = 5

    with pytest.raises(ValueError, match="already finished"):
        check_round_correct(template_game, _round_input())
