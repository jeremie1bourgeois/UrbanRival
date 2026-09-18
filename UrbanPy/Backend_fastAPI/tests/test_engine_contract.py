"""
Le contrat du moteur pur (src/core/engine/contract.py) doit être complet : jouer un round depuis la forme compacte
(deck compilé + état) donne exactement le même état qu'avec les objets d'origine, quelles que soient les mains et
les actions — c'est ce qui prouve que l'état contient tout ce que le moteur lit. Et son vocabulaire figé doit couvrir
tout ce que le parseur produit.
"""
import random

from src.adapters.repositories.card_repository import _official_cards, all_capacity_descriptions
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.engine.contract import (CLANS, CONDITIONS, HOWS, TARGETS, TYPES, capacity_from_compiled,
                                      compile_capacity, deck_from_game, game_from_state, state_from_game)
from src.core.engine.hands import random_hand
from src.core.parsing.capacity_parser import parse_capacity
from src.core.services.game_service import check_end
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import GameResult, ProcessRoundInput


def _parsed_capacities():
    return [parsed.capacity for parsed in map(parse_capacity, all_capacity_descriptions()) if parsed.capacity]


def test_vocabulary_covers_every_parsed_capacity():
    for capacity in _parsed_capacities():
        assert capacity.how in HOWS
        assert capacity.target in TARGETS
        assert set(capacity.types) <= set(TYPES)
        for condition in capacity.effect_conditions:
            name, _, clans = condition.partition(":")
            assert ("bet" if name.startswith("bet") else name) in CONDITIONS
            assert not clans or set(clans.split("|")) <= set(CLANS)


def test_clans_are_the_official_factions():
    assert set(CLANS) == {card_data.get("faction", "") for card_data in _official_cards().values()}


def test_compiled_capacity_round_trip():
    for capacity in _parsed_capacities():
        back = capacity_from_compiled(compile_capacity(capacity))
        assert (back.how, back.target, back.value, back.borne) == (capacity.how, capacity.target, capacity.value, capacity.borne)
        assert sorted(back.types) == sorted(capacity.types)
        assert sorted(back.effect_conditions) == sorted(capacity.effect_conditions)


def _new_game(rng: random.Random) -> Game:
    game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [])
    game.ally.cards, game.enemy.cards = random_hand(rng), random_hand(rng)
    return game


def _random_round(rng: random.Random, game: Game) -> ProcessRoundInput:
    def pick(player):
        index = rng.choice([i for i, card in enumerate(player.cards) if not card.played])
        fury = player.pillz >= 3 and rng.random() < 0.2
        return index, rng.randint(1, player.pillz + 1 - (3 if fury else 0)), fury
    (ally_index, ally_pillz, ally_fury), (enemy_index, enemy_pillz, enemy_fury) = pick(game.ally), pick(game.enemy)
    return ProcessRoundInput(player1_card_index=ally_index, player1_pillz=ally_pillz, player1_fury=ally_fury,
                             player2_card_index=enemy_index, player2_pillz=enemy_pillz, player2_fury=enemy_fury)


def test_replaying_from_compact_state_gives_the_same_state():
    rng = random.Random(0)
    for _ in range(300):
        game = _new_game(rng)
        deck = deck_from_game(game)
        while check_end(game) == GameResult.NONE:
            state = state_from_game(game)
            rebuilt = game_from_state(deck, state)
            assert state_from_game(rebuilt) == state
            assert deck_from_game(rebuilt) == deck
            round_data = _random_round(rng, game)
            for candidate in (game, rebuilt):
                check_round_correct(candidate, round_data)
                process_round(candidate, round_data)
            assert state_from_game(rebuilt) == state_from_game(game)
