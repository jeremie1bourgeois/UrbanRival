"""
API moteur pure (feuille de route D1) : un état, deux actions, un pas, sans persistance ni I/O.
C'est le contrat sur lequel se branchent les adversaires de recherche et, plus tard, l'environnement d'apprentissage.
"""
import copy
import os

import pytest

from src.core.ai import engine
from src.core.ai.engine import Pick, StepResult
from src.core.domain.game import NB_ROUNDS
from src.schemas.game_schemas import GameResult


def test_legal_actions_enumerate_unplayed_cards_pillz_and_affordable_fury(template_game):
    template_game.ally.pillz = 3
    template_game.ally.cards[0].played = True

    actions = engine.legal_actions(template_game, "ally")

    assert {a.card_index for a in actions} == {1, 2, 3}
    assert {a.pillz for a in actions if not a.fury} == {1, 2, 3, 4}   # 0 à 3 pillz misées
    assert {a.pillz for a in actions if a.fury} == {1}                # fury (3 pillz) + 0 misée seulement


def test_legal_actions_are_empty_on_a_finished_game(template_game):
    template_game.nb_turn = NB_ROUNDS + 1

    assert engine.legal_actions(template_game, "ally") == []
    assert engine.legal_actions(template_game, "enemy") == []


def test_step_leaves_the_state_it_receives_untouched(template_game):
    before = copy.deepcopy(template_game.to_dict())

    engine.step(template_game, Pick(0, 3), Pick(1, 2))

    assert template_game.to_dict() == before


def test_step_returns_a_new_state_where_the_round_was_played(template_game):
    state, result = engine.step(template_game, Pick(0, 3), Pick(1, 2))

    assert isinstance(result, StepResult)
    assert state.nb_turn == template_game.nb_turn + 1
    assert state.ally.cards[0].played and state.enemy.cards[1].played
    assert state.ally.pillz == template_game.ally.pillz - 2      # 1 pillz est toujours consommée
    assert state.enemy.pillz == template_game.enemy.pillz - 1
    assert len(state.history) == len(template_game.history) + 1
    assert result.round.ally.win != result.round.enemy.win
    assert result.result is GameResult.NONE and result.done is False


def test_step_in_place_plays_the_round_on_the_state_itself(template_game):
    state, _ = engine.step(template_game, Pick(0, 3), Pick(1, 2), in_place=True)

    assert state is template_game
    assert template_game.nb_turn == 2


def test_step_journal_can_be_turned_off_without_changing_the_state(template_game):
    with_log, result_with = engine.step(template_game, Pick(0, 3), Pick(1, 2))
    without_log, result_without = engine.step(template_game, Pick(0, 3), Pick(1, 2), log=False)

    assert result_with.log and result_without.log == []
    assert _without_logs(without_log.to_dict()) == _without_logs(with_log.to_dict())


def test_step_refuses_an_illegal_action(template_game):
    template_game.ally.cards[0].played = True

    with pytest.raises(ValueError):
        engine.step(template_game, Pick(0, 1), Pick(1, 1))
    with pytest.raises(ValueError):
        engine.step(template_game, Pick(1, 99), Pick(1, 1))


def test_clone_is_independent_and_faithful(template_game):
    clone = engine.clone(template_game)

    assert clone is not template_game
    assert clone.to_dict() == template_game.to_dict()
    clone.ally.life = 1
    clone.ally.cards[0].played = True
    assert template_game.ally.life != 1 and not template_game.ally.cards[0].played


def test_result_and_reward_follow_the_life_totals(template_game):
    template_game.nb_turn = NB_ROUNDS + 1

    template_game.ally.life, template_game.enemy.life = 5, 3
    assert engine.is_terminal(template_game) and engine.result(template_game) is GameResult.ALLY
    assert engine.reward(template_game, "ally") == 1 and engine.reward(template_game, "enemy") == -1

    template_game.ally.life, template_game.enemy.life = 3, 5
    assert engine.result(template_game) is GameResult.ENEMY
    assert engine.reward(template_game, "ally") == -1

    template_game.ally.life = 5
    assert engine.result(template_game) is GameResult.DRAW
    assert engine.reward(template_game, "ally") == 0 == engine.reward(template_game, "enemy")


def test_a_player_at_zero_life_ends_the_game(template_game):
    template_game.enemy.life = 0

    assert engine.is_terminal(template_game)
    assert engine.result(template_game) is GameResult.ALLY
    assert engine.reward(template_game, "ally") == 1


def test_reward_is_zero_while_the_game_is_running(template_game):
    assert engine.reward(template_game, "ally") == 0
    assert engine.reward(template_game, "enemy") == 0


def test_new_game_builds_a_playable_state_without_touching_the_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    game = engine.new_game([("Agustino", 2), ("Allison", 3), ("Amelia", 3), ("Ashley", 2)],
                           [("Asporov", 4), ("Bhudd", 3), ("Amelia", 3), ("Ashley", 2)])

    assert game.nb_turn == 1 and game.turn is True
    assert (game.ally.life, game.ally.pillz) == (12, 12) == (game.enemy.life, game.enemy.pillz)
    assert [card.name for card in game.ally.cards] == ["Agustino", "Allison", "Amelia", "Ashley"]
    assert engine.legal_actions(game, "ally")
    assert os.listdir(tmp_path) == []          # aucune partie écrite sur le disque


def test_a_game_played_to_the_end_is_terminal_and_has_a_winner(template_game):
    state = template_game
    while not engine.is_terminal(state):
        ally = engine.legal_actions(state, "ally")[0]
        enemy = engine.legal_actions(state, "enemy")[0]
        state, result = engine.step(state, ally, enemy)

    assert result.done is True
    assert engine.result(state) in (GameResult.ALLY, GameResult.ENEMY, GameResult.DRAW)
    assert state.nb_turn > NB_ROUNDS or 0 in (state.ally.life, state.enemy.life)


def _without_logs(state: dict) -> dict:
    """État sans les journaux de round (les fixtures de rejeu comparent l'état de la même façon)."""
    return {**state, "history": [{**round_, "log": []} for round_ in state["history"]]}
