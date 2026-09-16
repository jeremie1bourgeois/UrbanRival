"""Adversaires automatiques : leurs choix sont toujours légaux (carte non jouée, pillz disponibles, fury payable)."""
import random

import pytest

from src.core.ai.opponent import STRATEGIES, Pick, heuristic_pick, legal_picks, random_pick
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import ProcessRoundInput


def is_legal(game, pick: Pick, side: str) -> bool:
    player = game.enemy if side == "enemy" else game.ally
    if player.cards[pick.card_index].played:
        return False
    return 1 <= pick.pillz and pick.pillz - 1 + (3 if pick.fury else 0) <= player.pillz


def test_legal_picks_enumerate_unplayed_cards_pillz_and_affordable_fury(template_game):
    template_game.enemy.pillz = 3
    template_game.enemy.cards[1].played = True

    picks = legal_picks(template_game, "enemy")

    assert {p.card_index for p in picks} == {0, 2, 3}
    assert {p.pillz for p in picks if not p.fury} == {1, 2, 3, 4}          # 0 à 3 pillz misées
    assert {p.pillz for p in picks if p.fury} == {1}                        # fury (3) + 0 misée seulement
    assert all(is_legal(template_game, p, "enemy") for p in picks)


@pytest.fixture
def installed_trained_policy():
    """
    La stratégie « trained » lit une IA sur disque, absente d'un dépôt frais. On en installe une en mémoire
    (poids nuls = jeu aléatoire) pour que le balayage de légalité la couvre comme les autres, puis on nettoie :
    sans cela, le cache fuiterait sur les tests suivants, qui la supposent indisponible.
    """
    from src.core.ai import trained
    from src.core.ai.policy import LinearPolicy
    trained.forget_cached_policy()
    trained._cache[trained.DEFAULT_POLICY_PATH] = LinearPolicy()
    yield
    trained.forget_cached_policy()


@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_strategies_only_return_legal_picks_over_a_whole_game(template_game, strategy, installed_trained_policy):
    rng = random.Random(42)
    for _ in range(4):
        enemy_pick = STRATEGIES[strategy](template_game, "enemy", rng)
        assert is_legal(template_game, enemy_pick, "enemy")
        ally_pick = STRATEGIES[strategy](template_game, "ally", rng)
        assert is_legal(template_game, ally_pick, "ally")
        round_data = ProcessRoundInput(player1_card_index=ally_pick.card_index, player1_pillz=ally_pick.pillz, player1_fury=ally_pick.fury,
                                       player2_card_index=enemy_pick.card_index, player2_pillz=enemy_pick.pillz, player2_fury=enemy_pick.fury)
        check_round_correct(template_game, round_data)
        process_round(template_game, round_data)
        if template_game.ally.life == 0 or template_game.enemy.life == 0:
            break


def test_random_pick_is_reproducible_with_a_seed(template_game):
    first = random_pick(template_game, "enemy", random.Random(7))
    second = random_pick(template_game, "enemy", random.Random(7))

    assert first == second


def test_heuristic_spreads_pillz_over_the_remaining_rounds(template_game):
    pick = heuristic_pick(template_game, "enemy", random.Random(0))   # round 1, 12 pillz, 4 rounds : ~3 par round

    assert 2 <= pick.pillz - 1 <= 4
    assert pick.fury is False


def test_heuristic_spends_everything_on_the_last_round(template_game):
    template_game.nb_turn = 4
    template_game.enemy.pillz = 5
    for index in (0, 1, 2):
        template_game.enemy.cards[index].played = True

    pick = heuristic_pick(template_game, "enemy", random.Random(0))

    assert pick.card_index == 3
    assert pick.pillz - 1 + (3 if pick.fury else 0) == 5
