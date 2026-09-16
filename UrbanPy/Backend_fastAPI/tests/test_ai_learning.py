"""
Les critères, la politique, l'arène et l'entraînement.

Ces tests restent volontairement petits et rapides : ils vérifient la **mécanique** (le compte des critères, le
tirage au sort, l'équité de l'arène, la forme de l'entraînement), pas le niveau de jeu. Mesurer le niveau
demande des milliers de parties — c'est le rôle de `scripts/evaluate_ai.py`, pas de la suite de tests.
"""
import random

import pytest

from src.core.ai.arena import DuelResult, duel, play_game
from src.core.ai.engine_api import DeckPool, new_game
from src.core.ai.features import FEATURE_COUNT, FEATURE_NAMES, feature_vector
from src.core.ai.opponent import STRATEGIES, Pick, legal_picks
from src.core.ai.policy import LinearPolicy, policy_strategy, random_policy
from src.core.ai.train import TrainingConfig, train


@pytest.fixture
def game(template_game):
    return new_game(template_game.ally.cards, template_game.enemy.cards)


@pytest.fixture
def pool(template_data):
    """Un réservoir minuscule bâti sur les cartes du template : pas de lecture du catalogue complet."""
    class TemplatePool(DeckPool):
        def __init__(self, cards):
            self._cards = cards

        def deck(self, rng, size=4):
            import copy
            return [copy.deepcopy(card) for card in rng.sample(self._cards, size)]

        def matchup(self, rng, size=4):
            return self.deck(rng, size), self.deck(rng, size)

    from src.core.domain.game import Game
    loaded = Game.from_dict_template(template_data)
    return TemplatePool(loaded.ally.cards + loaded.enemy.cards)


# --------------------------------------------------------------------- critères

def test_every_criterion_has_a_name_and_a_value(game):
    vector = feature_vector(game, "ally", Pick(0, 1, False))

    assert len(vector) == FEATURE_COUNT == len(FEATURE_NAMES)
    assert all(isinstance(value, float) for value in vector)


def test_criteria_stay_on_a_comparable_scale(game):
    """Un critère qui partirait à 50 pendant que les autres valent 0,3 écraserait tout le reste."""
    for pick in legal_picks(game, "ally"):
        for name, value in zip(FEATURE_NAMES, feature_vector(game, "ally", pick)):
            assert -3.0 <= value <= 3.0, f"le critère {name} vaut {value}, hors de l'échelle attendue"


def test_betting_more_pillz_raises_the_estimated_attack(game):
    small = feature_vector(game, "ally", Pick(0, 2, False))
    large = feature_vector(game, "ally", Pick(0, 8, False))
    index = FEATURE_NAMES.index("attaque_estimee")

    assert large[index] > small[index]


def test_fury_raises_the_damage_criterion(game):
    without = feature_vector(game, "ally", Pick(0, 1, False))
    with_fury = feature_vector(game, "ally", Pick(0, 1, True))
    index = FEATURE_NAMES.index("degats")

    assert with_fury[index] > without[index]


def test_the_two_sides_read_the_same_situation_from_their_own_point_of_view(game):
    game.ally.life, game.enemy.life = 10, 4
    index = FEATURE_NAMES.index("avance_en_vie")

    ally_view = feature_vector(game, "ally", Pick(0, 1, False))[index]
    enemy_view = feature_vector(game, "enemy", Pick(0, 1, False))[index]

    assert ally_view > 0 > enemy_view


# -------------------------------------------------------------------- politique

def test_a_policy_with_zero_weights_plays_uniformly_at_random(game):
    """C'est la propriété qui rend l'entraînement possible : on démarre au niveau du jeu aléatoire."""
    policy = LinearPolicy()
    rng = random.Random(0)

    picks = {policy.pick(game, "ally", rng) for _ in range(200)}

    assert len(picks) > 20          # il explore vraiment, il ne répète pas un seul coup


def test_greedy_mode_always_plays_the_best_scored_move(game):
    policy = random_policy(random.Random(3), scale=1.0)

    chosen = policy.pick(game, "ally", random.Random(0), greedy=True)
    best = max(legal_picks(game, "ally"), key=lambda pick: policy.score(game, "ally", pick))

    assert policy.score(game, "ally", chosen) == pytest.approx(policy.score(game, "ally", best))


def test_big_weights_make_the_policy_decisive(game):
    """Plus les poids sont grands, plus l'IA joue souvent son coup préféré : elle apprend aussi sa conviction."""
    timid = LinearPolicy(weights=[0.0] + [0.1] * (FEATURE_COUNT - 1))
    decisive = LinearPolicy(weights=[0.0] + [10.0] * (FEATURE_COUNT - 1))
    rng = random.Random(1)

    timid_picks = len({timid.pick(game, "ally", rng) for _ in range(150)})
    decisive_picks = len({decisive.pick(game, "ally", rng) for _ in range(150)})

    assert decisive_picks < timid_picks


def test_action_probabilities_sum_to_one_and_favour_the_best(game):
    policy = random_policy(random.Random(5), scale=1.0)

    probabilities = policy.action_probabilities(game, "ally")

    assert sum(probability for _, probability in probabilities) == pytest.approx(1.0)
    assert probabilities[0][1] >= probabilities[-1][1]


def test_huge_weights_do_not_blow_up_the_exponential(game):
    """exp(1000) déborderait ; le calcul retire le maximum d'abord."""
    policy = LinearPolicy(weights=[500.0] * FEATURE_COUNT)

    assert policy.pick(game, "ally", random.Random(0)) is not None


def test_a_policy_survives_a_round_trip_through_a_file(tmp_path):
    policy = random_policy(random.Random(7), scale=0.8)
    policy.meta = {"entrainement": "essai"}
    path = str(tmp_path / "ia.json")

    policy.save(path)
    reloaded = LinearPolicy.load(path)

    assert reloaded.weights == pytest.approx(policy.weights)
    assert reloaded.meta == {"entrainement": "essai"}


def test_a_file_written_with_other_criteria_is_refused_rather_than_misread(tmp_path):
    """Sans ce garde-fou, un vieux fichier serait relu avec les poids dans le désordre — en silence."""
    path = tmp_path / "vieux.json"
    path.write_text('{"format_version": 1, "features": ["autre_critere"], "weights": {"autre_critere": 1.0}}')

    with pytest.raises(ValueError, match="autres critères"):
        LinearPolicy.load(str(path))


def test_a_wrong_number_of_weights_is_refused():
    with pytest.raises(ValueError, match="poids fournis"):
        LinearPolicy(weights=[0.1, 0.2])


# ------------------------------------------------------------------------ arène

def test_a_strategy_against_itself_wins_about_half(pool):
    """Contrôle de bon sens : si ce test dérive loin de 50 %, l'arène est biaisée."""
    result = duel(STRATEGIES["random"], STRATEGIES["random"], pool, games=120, rng=random.Random(2))

    assert 0.3 < result.win_rate < 0.7


def test_swapping_sides_makes_a_deck_advantage_cancel_out(pool):
    """Chaque paire de decks est jouée deux fois, camps inversés : le nombre de parties est donc pair."""
    result = duel(STRATEGIES["random"], STRATEGIES["heuristic"], pool, games=40, rng=random.Random(4))

    assert result.games == 40
    assert result.wins + result.losses + result.draws == 40


def test_the_margin_of_error_shrinks_as_games_pile_up():
    few = DuelResult(games=40, wins=24, losses=16, draws=0, mean_life_gap=1.0)
    many = DuelResult(games=4000, wins=2400, losses=1600, draws=0, mean_life_gap=1.0)

    assert few.win_rate == pytest.approx(many.win_rate)
    assert many.margin < few.margin
    assert many.conclusive and not few.conclusive


def test_draws_count_as_half_a_win():
    result = DuelResult(games=10, wins=4, losses=4, draws=2, mean_life_gap=0.0)

    assert result.win_rate == pytest.approx(0.5)


def test_a_played_game_reaches_an_end(pool):
    rng = random.Random(0)
    outcome = play_game(STRATEGIES["random"], STRATEGIES["heuristic"], pool.deck(rng), pool.deck(rng), rng)

    assert outcome.winner in ("ally", "enemy", "draw")
    assert 1 <= outcome.rounds <= 4


# ------------------------------------------------------------------ entraînement

def test_training_returns_a_usable_policy_and_one_report_per_generation(pool):
    config = TrainingConfig(generations=3, population=6, games_per_candidate=4, opponent="random", seed=0)

    policy, reports = train(config, pool=pool)

    assert len(policy.weights) == FEATURE_COUNT
    assert len(reports) == 3
    assert [report.generation for report in reports] == [1, 2, 3]
    assert policy.meta["adversaire"] == "random"


def test_the_same_seed_gives_exactly_the_same_training(pool):
    """L'entraînement doit être reproductible, sinon on ne peut comparer deux réglages."""
    config = TrainingConfig(generations=2, population=6, games_per_candidate=4, opponent="random", seed=3)

    first, _ = train(config, pool=pool)
    second, _ = train(config, pool=pool)

    assert first.weights == pytest.approx(second.weights)


def test_two_different_seeds_explore_differently(pool):
    a, _ = train(TrainingConfig(generations=2, population=6, games_per_candidate=4, opponent="random", seed=1), pool=pool)
    b, _ = train(TrainingConfig(generations=2, population=6, games_per_candidate=4, opponent="random", seed=2), pool=pool)

    assert a.weights != pytest.approx(b.weights)


def test_exploration_never_collapses_to_zero(pool):
    """Une exploration nulle fige l'IA : la recherche cesse d'apprendre quoi que ce soit."""
    _, reports = train(TrainingConfig(generations=5, population=6, games_per_candidate=4,
                                      opponent="random", seed=0), pool=pool)

    assert all(report.spread > 0 for report in reports)


def test_self_play_trains_against_the_current_version(pool):
    config = TrainingConfig(generations=2, population=6, games_per_candidate=4, opponent="self", seed=0)

    policy, reports = train(config, pool=pool)

    assert policy.meta["adversaire"] == "self"
    assert len(reports) == 2


def test_an_unknown_training_opponent_is_refused(pool):
    config = TrainingConfig(generations=1, population=4, games_per_candidate=4, opponent="grandmaster", seed=0)

    with pytest.raises(ValueError, match="Adversaire inconnu"):
        train(config, pool=pool)


def test_the_policy_learned_beats_the_random_baseline_it_trained_against(pool):
    """
    Le seul test de niveau, gardé volontairement modeste : après un entraînement court contre le jeu aléatoire,
    l'IA doit faire mieux que le hasard. La barre est basse exprès — le vrai verdict vient d'evaluate_ai.py.
    """
    config = TrainingConfig(generations=6, population=12, games_per_candidate=20, opponent="random", seed=0)
    policy, _ = train(config, pool=pool)

    result = duel(policy_strategy(policy), STRATEGIES["random"], pool, games=200, rng=random.Random(77))

    assert result.win_rate > 0.5
