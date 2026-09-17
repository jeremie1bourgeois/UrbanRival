"""
Solveur exact de fin de partie (`src/core/ai/solver.py`) : induction arrière sur l'état public, un jeu matriciel
par carte du premier joueur. Attentes calculées à la main sur des fins de partie minuscules, avec des cartes
sans pouvoir et de clans tous différents (bonus inactifs) : attaque = puissance × pillz, égalité à la carte
qui a le moins d'étoiles, puis à celui qui a joué en premier.

Cartes utilisées (niveau : puissance / dégâts) — Wardog 2★ : 8/2 (La Junta), Lilith 3★ : 5/4 (GHEIST),
Nanook Cr 3★ : 8/4 (Ulu Watu), Natrang 3★ : 4/4 (Fang Pi Clang), Meroo 1★ : 5/1 (Bangers).
"""
import random

import pytest

from src.core.ai import engine, solver
from src.core.ai.engine import Pick
from src.core.ai.opponent import STRATEGIES, minimax_pick
from src.core.domain.game import NB_ROUNDS


@pytest.fixture(autouse=True)
def fresh_cache():
    """Chaque test part d'un solveur vierge : la mémoïsation est globale au processus."""
    solver.clear_cache()


def endgame(ally, enemy, life, pillz, ally_first, rounds_left=1):
    """Fin de partie : `ally` / `enemy` sont les cartes restantes `[(nom, étoiles), ...]`, une par round restant."""
    state = engine.new_game(ally, enemy, life=1, pillz=0, ally_first=ally_first)
    state.nb_turn = NB_ROUNDS - rounds_left + 1
    state.ally.life, state.enemy.life = life
    state.ally.pillz, state.enemy.pillz = pillz
    return state


def test_a_last_round_won_whatever_the_opponent_does_is_worth_one():
    """
    Wardog (8) contre Lilith (5), 3 pillz chacun, l'allié meurt s'il perd le round et tue s'il le gagne.
    24 ou 32 d'attaque (2 ou 3 pillz misées) battent les 20 au mieux de Lilith : victoire certaine.
    """
    state = endgame([("Wardog", 2)], [("Lilith", 3)], life=(3, 2), pillz=(3, 3), ally_first=True)

    solution = solver.solve(state)

    assert solution.value == pytest.approx(1)
    assert solution.first == "ally" and solution.card == 0
    assert set(solution.bets) <= {Pick(0, 3), Pick(0, 4)}
    assert sum(solution.bets.values()) == pytest.approx(1)


def test_the_fury_is_taken_when_it_is_the_only_way_to_win():
    """
    Meroo (5/1) contre Natrang (4/4), 1 vie contre 2, 3 pillz contre 0. Meroo gagne le round quoi qu'il arrive
    (5 > 4) mais 1 dégât laisse 1 vie partout : nulle. Avec la fury (3 dégâts), c'est le KO : seule mise gagnante.
    """
    state = endgame([("Meroo", 1)], [("Natrang", 3)], life=(1, 2), pillz=(3, 0), ally_first=True)

    solution = solver.solve(state)

    assert solution.value == pytest.approx(1)
    assert solution.bets == {Pick(0, 1, fury=True): pytest.approx(1)}


def test_a_last_round_lost_whatever_we_do_is_worth_minus_one():
    """Lilith (5/4) sans pillz contre Wardog (8/2) avec 1 pillz : 5 < 8, l'allié perd le round et ses 3 vies."""
    state = endgame([("Lilith", 3)], [("Wardog", 2)], life=(3, 5), pillz=(0, 1), ally_first=False)

    assert solver.value(state) == pytest.approx(-1)


def test_a_tiny_third_round_is_a_coin_flip_whose_answer_depends_on_the_card_seen():
    """
    Round 3, l'allié pose en premier : Wardog (8/2) et Meroo (5/1) contre Lilith (5/4) et Natrang (4/4),
    5 vies et 1 pillz chacun. Calcul à la main (le round 4 se joue avec les cartes et pillz qui restent,
    ennemi en premier ; +1 / -1 = partie gagnée / perdue aux vies) :

    Wardog posé, mise 0 / 1 contre (Lilith 0, Lilith 1, Natrang 0, Natrang 1) :  [1, -1, 1, 1] / [-1, 1, -1, 1]
    Meroo posé, mise 0 / 1 contre les mêmes :                                   [1, -1, 1, -1] / [1, 1, -1, 1]

    Chaque carte donne un pile ou face : valeur 0, mise 0 ou 1 à parts égales. L'ennemi, lui, répond selon
    la carte vue : contre Meroo, Lilith avec 1 pillz ou Natrang sans (moitié-moitié, seul équilibre) ;
    contre Wardog, Lilith avec 1 pillz une fois sur deux, et jamais Natrang avec 1 pillz (perdant partout).
    """
    state = endgame([("Wardog", 2), ("Meroo", 1)], [("Lilith", 3), ("Natrang", 3)],
                    life=(5, 5), pillz=(1, 1), ally_first=True, rounds_left=2)

    solution = solver.solve(state)

    assert solution.value == pytest.approx(0)
    assert solution.card_values == {0: pytest.approx(0), 1: pytest.approx(0)}
    assert solution.bets == {Pick(solution.card, 1): pytest.approx(0.5), Pick(solution.card, 2): pytest.approx(0.5)}
    assert solution.replies[1] == {Pick(0, 2): pytest.approx(0.5), Pick(1, 1): pytest.approx(0.5)}
    assert solution.replies[0][Pick(0, 2)] == pytest.approx(0.5)
    assert Pick(1, 2) not in solution.replies[0]
    assert solution.replies[0] != solution.replies[1]


def test_an_already_solved_state_is_not_solved_again(monkeypatch):
    """Mémoïsation sur l'état public : deux objets égaux (mêmes mains, vies, pillz, cartes jouées) partagent la solution."""
    calls = []
    real_solve_matrix = solver.solve_matrix
    monkeypatch.setattr(solver, "solve_matrix", lambda matrix: calls.append(1) or real_solve_matrix(matrix))
    make = lambda: endgame([("Wardog", 2), ("Meroo", 1)], [("Lilith", 3), ("Natrang", 3)],
                           life=(5, 5), pillz=(1, 1), ally_first=True, rounds_left=2)

    first = solver.solve(make())
    solved_once = len(calls)
    second = solver.solve(make())

    assert solved_once > 0
    assert len(calls) == solved_once
    assert second == first


def coin_flip_third_round():
    return endgame([("Wardog", 2), ("Meroo", 1)], [("Lilith", 3), ("Natrang", 3)],
                   life=(5, 5), pillz=(1, 1), ally_first=True, rounds_left=2)


def test_playing_first_the_solver_keeps_its_card_and_draws_its_bet():
    """Carte pure, mise tirée au sort : sur 40 tirages, toujours la même carte, les deux mises apparaissent."""
    rng = random.Random(7)
    state = coin_flip_third_round()

    picks = {solver.solver_pick(state, "ally", rng) for _ in range(40)}

    assert {pick.card_index for pick in picks} == {solver.solve(state).card}
    assert {pick.pillz for pick in picks} == {1, 2}


def test_playing_second_the_solver_answers_the_card_it_sees():
    """Meroo en face : Lilith avec 1 pillz ou Natrang sans, jamais autre chose (voir le calcul à la main plus haut)."""
    rng = random.Random(7)
    state = coin_flip_third_round()

    picks = {solver.solver_pick(state, "enemy", rng, revealed_card=1) for _ in range(40)}

    assert picks == {Pick(0, 2), Pick(1, 1)}


def test_before_the_last_two_rounds_the_solver_plays_like_minimax(template_game):
    """Les rounds 1 et 2 ne sont pas résolus (étape 4) : en attendant, le coup est celui du minimax."""
    expected = minimax_pick(template_game, "enemy", random.Random(3))

    assert solver.solver_pick(template_game, "enemy", random.Random(3)) == expected


def test_the_solver_is_a_registered_strategy():
    assert STRATEGIES["solver"] is solver.solver_pick
