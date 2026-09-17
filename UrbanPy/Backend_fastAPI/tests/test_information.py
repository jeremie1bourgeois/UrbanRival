"""
Ordre de jeu et information du round (règle Urban Rivals confirmée par l'utilisateur, 2026-09-17) :
le premier joueur pose une carte **visible**, mais ses pillz restent cachées ; le second choisit en voyant
cette carte. Le premier joueur est tiré au sort au round 1, puis alterne.
"""
import random

import pytest

from src.core.ai import arena, engine
from src.core.ai.engine import ELO_LIFE, Pick
from src.core.ai.opponent import STRATEGIES, _sample_replies, minimax_pick
from src.core.domain.game import NB_ROUNDS

HAND = [("Agustino", 2), ("Allison", 3), ("Amelia", 3), ("Ashley", 2)]


def test_new_game_can_start_with_either_player(template_game):
    ally_first = engine.new_game(HAND, HAND, ally_first=True)
    enemy_first = engine.new_game(HAND, HAND, ally_first=False)

    assert engine.first_side(ally_first) == "ally" and engine.plays_first(ally_first, "ally")
    assert engine.first_side(enemy_first) == "enemy" and engine.plays_first(enemy_first, "enemy")
    assert not engine.plays_first(enemy_first, "ally")


def test_elo_game_starts_at_14_lives_with_a_drawn_first_player():
    game = engine.elo_game(HAND, HAND, random.Random(0))

    assert (game.ally.life, game.enemy.life) == (ELO_LIFE, ELO_LIFE)
    assert (game.ally.pillz, game.enemy.pillz) == (12, 12)
    assert game.nb_turn == 1
    drawn = {engine.first_side(engine.elo_game(HAND, HAND, random.Random(seed))) for seed in range(20)}
    assert drawn == {"ally", "enemy"}          # le premier joueur est bien tiré au sort


def test_the_first_player_alternates_from_one_round_to_the_next(template_game):
    first = engine.first_side(template_game)

    state, _ = engine.step(template_game, Pick(0, 1), Pick(0, 1))

    assert engine.first_side(state) != first


def test_play_out_reveals_the_first_players_card_to_the_second_only(template_game):
    calls = []

    def spy(game, side, rng, revealed_card=None):
        calls.append((side, revealed_card, engine.first_side(game)))
        return engine.legal_actions(game, side)[0]

    engine.play_out(template_game, {"ally": spy, "enemy": spy}, random.Random(0))

    for index in range(0, len(calls), 2):
        first_call, second_call = calls[index], calls[index + 1]
        first_side = first_call[2]
        assert first_call[0] == first_side and first_call[1] is None      # le premier joue en aveugle
        assert second_call[0] != first_side and second_call[1] is not None  # le second voit la carte


def test_a_search_that_knows_the_opponents_card_only_considers_that_card(template_game):
    replies = _sample_replies(template_game, "enemy", random.Random(0), nb_replies=8, revealed_card=2)

    assert replies and {reply.card_index for reply in replies} == {2}


def test_a_search_without_reveal_considers_every_card_left(template_game):
    replies = _sample_replies(template_game, "enemy", random.Random(0), nb_replies=20, revealed_card=None)

    assert {reply.card_index for reply in replies} == {0, 1, 2, 3}


@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_every_strategy_accepts_a_revealed_card_and_stays_legal(template_game, strategy):
    pick = STRATEGIES[strategy](template_game, "ally", random.Random(1), revealed_card=1)

    assert pick in engine.legal_actions(template_game, "ally")


def test_knowing_which_card_the_opponent_played_changes_the_answer(template_game):
    """
    Jouer en second contre Bhudd (3 étoiles) ou contre Serafina (5 étoiles, 8/8) n'appelle pas la même réponse :
    à graine égale, la recherche répond différemment selon la carte révélée — l'information est bien utilisée.
    """
    answers = {index: minimax_pick(template_game, "ally", random.Random(0), revealed_card=index)
               for index in range(len(template_game.enemy.cards))}

    assert all(answer in engine.legal_actions(template_game, "ally") for answer in answers.values())
    assert len(set(answers.values())) > 1


def test_the_last_round_leaves_nothing_to_reveal(template_game):
    """Au dernier round il ne reste qu'une carte à chacun : la révélation n'apprend rien, la réponse est la même."""
    state = _last_round(template_game, ally_life=12, enemy_life=12, ally_pillz=11, enemy_pillz=11, enemy_card=3)

    assert minimax_pick(state, "ally", random.Random(0), revealed_card=3) == minimax_pick(state, "ally", random.Random(0))


def test_arena_plays_elo_games(template_game):
    rng = random.Random(4)
    hands = arena.mirrored_hands(rng)

    result = arena.duel(STRATEGIES["random"], STRATEGIES["random"], nb_games=4, rng=rng,
                        hands_factory=lambda _: hands)

    assert result.games == 4


def _last_round(game, ally_life, enemy_life, ally_pillz, enemy_pillz, ally_card=3, enemy_card=3):
    game.nb_turn = NB_ROUNDS
    game.ally.life, game.enemy.life = ally_life, enemy_life
    game.ally.pillz, game.enemy.pillz = ally_pillz, enemy_pillz
    for index in range(len(game.ally.cards)):
        game.ally.cards[index].played = index != ally_card
        game.enemy.cards[index].played = index != enemy_card
    return game
