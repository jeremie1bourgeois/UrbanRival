"""
Le moteur de référence (src/core/engine/reference.py) doit dire la même chose que process_round et game_service :
legal_actions = exactement les coups que check_round_correct accepte, step déterministe et sans effet de bord,
terminal = check_end.
"""
import random

import pytest

from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.engine.contract import Action, deck_from_game, game_from_state, state_from_game
from src.core.engine.hands import random_hand
from src.core.engine.reference import legal_actions, play, step, terminal
from src.core.services.game_service import check_end
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput

SCORE_OF_RESULT = {GameResult.ALLY: 1.0, GameResult.ENEMY: 0.0, GameResult.DRAW: 0.5, GameResult.NONE: None}


def _random_playout(rng: random.Random):
    """Les états successifs d'une partie jouée au hasard, jusqu'à l'état final compris."""
    game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [])
    game.ally.cards, game.enemy.cards = random_hand(rng), random_hand(rng)
    deck, state = deck_from_game(game), state_from_game(game)
    yield deck, state
    while terminal(state) is None:
        state = step(deck, state, rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy")))
        yield deck, state


def _accepted_by_engine(deck, state, side: str) -> set:
    """Tous les coups (carte, pillz, fury) que check_round_correct accepte pour ce camp, par force brute."""
    other_player = state.enemy if side == "ally" else state.ally
    other = Action(other_player.played.index(False), 1, False)     # un coup sûrement valide pour l'autre camp
    accepted = set()
    for card in range(4):
        for pillz in range(0, 20):
            for fury in (False, True):
                own = Action(card, pillz, fury)
                ally, enemy = (own, other) if side == "ally" else (other, own)
                try:   # le schéma refuse déjà une mise < 1 ou un index hors main (ValidationError est un ValueError)
                    round_data = ProcessRoundInput(player1_card_index=ally.card, player1_pillz=ally.pillz, player1_fury=ally.fury,
                                                   player2_card_index=enemy.card, player2_pillz=enemy.pillz, player2_fury=enemy.fury)
                    check_round_correct(game_from_state(deck, state), round_data)
                    accepted.add(own)
                except ValueError:
                    pass
    return accepted


def test_fresh_game_has_92_actions_per_side():
    deck, state = next(_random_playout(random.Random(0)))
    assert len(legal_actions(state, "ally")) == 4 * (13 + 10)      # 13 mises sans fury + 10 avec (mise + 3 <= 12)


@pytest.mark.parametrize("seed", range(3))
def test_legal_actions_are_exactly_what_the_engine_accepts(seed):
    rng = random.Random(seed)
    for deck, state in _random_playout(rng):
        if terminal(state) is not None:
            break
        for side in ("ally", "enemy"):
            legal = legal_actions(state, side)
            assert len(legal) == len(set(legal))
            assert set(legal) == _accepted_by_engine(deck, state, side)


def test_step_is_deterministic_and_leaves_the_state_untouched():
    rng = random.Random(1)
    for _ in range(50):
        for deck, state in _random_playout(rng):
            if terminal(state) is not None:
                break
            before = state
            actions = rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy"))
            assert step(deck, state, *actions) == step(deck, state, *actions)
            assert state == before


def test_play_reports_the_fight_values_of_both_cards():
    rng = random.Random(4)
    for deck, state in _random_playout(rng):
        if terminal(state) is not None:
            break
        ally_action, enemy_action = rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy"))
        next_state, outcome = play(deck, state, ally_action, enemy_action)
        game = game_from_state(deck, state)
        process_round(game, ProcessRoundInput(player1_card_index=ally_action.card, player1_pillz=ally_action.pillz, player1_fury=ally_action.fury,
                                              player2_card_index=enemy_action.card, player2_pillz=enemy_action.pillz, player2_fury=enemy_action.fury))
        ally_card, enemy_card = game.ally.cards[ally_action.card], game.enemy.cards[enemy_action.card]
        assert next_state == step(deck, state, ally_action, enemy_action) == state_from_game(game)
        assert tuple(outcome.ally) == (ally_card.power_fight, ally_card.damage_fight, ally_card.attack, ally_card.win)
        assert tuple(outcome.enemy) == (enemy_card.power_fight, enemy_card.damage_fight, enemy_card.attack, enemy_card.win)
        assert outcome.ally.win != outcome.enemy.win


def test_terminal_matches_check_end():
    rng = random.Random(2)
    seen = set()
    for _ in range(200):
        for deck, state in _random_playout(rng):
            assert terminal(state) == SCORE_OF_RESULT[check_end(game_from_state(deck, state))]
            seen.add(terminal(state))
    assert seen == {None, 0.0, 0.5, 1.0}
