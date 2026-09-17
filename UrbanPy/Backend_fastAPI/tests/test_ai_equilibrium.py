"""
Équilibre de Nash d'un jeu matriciel à somme nulle (`src/core/ai/equilibrium.py`) : la brique de base du solveur.
Convention : la ligne maximise, la colonne minimise, `matrix[i][j]` est le gain de la ligne.
Attentes calculées à la main sur des jeux de référence.
"""
import pytest

from src.core.ai.equilibrium import solve_matrix


def test_matching_pennies_is_a_fifty_fifty_mix_worth_zero():
    """Pile ou face : aucun coup pur ne tient, chacun tire au sort à parts égales, la valeur est nulle."""
    solution = solve_matrix([[1, -1],
                             [-1, 1]])

    assert solution.value == pytest.approx(0)
    assert list(solution.row) == pytest.approx([0.5, 0.5])
    assert list(solution.column) == pytest.approx([0.5, 0.5])


def test_a_saddle_point_is_played_pure():
    """Ligne 2 domine (ses pires gains 3 ≥ tout ce que les autres offrent), colonne 1 domine : point-selle en (2, 1), valeur 3."""
    solution = solve_matrix([[1, 5, 2],
                             [3, 4, 6],
                             [0, 1, -1]])

    assert solution.value == pytest.approx(3)
    assert list(solution.row) == pytest.approx([0, 1, 0])
    assert list(solution.column) == pytest.approx([1, 0, 0])


def test_an_asymmetric_mix_has_the_hand_computed_value():
    """
    [[3, -1], [-2, 2]] : la ligne joue (p, 1-p) tel que 3p - 2(1-p) = -p + 2(1-p) → p = 1/2, valeur 1/2 ;
    la colonne joue (q, 1-q) tel que 3q - (1-q) = -2q + 2(1-q) → q = 3/8.
    """
    solution = solve_matrix([[3, -1],
                             [-2, 2]])

    assert solution.value == pytest.approx(0.5)
    assert list(solution.row) == pytest.approx([0.5, 0.5])
    assert list(solution.column) == pytest.approx([3 / 8, 5 / 8])


def test_a_symmetric_game_is_worth_zero_to_both():
    """Pierre-feuille-ciseaux : matrice antisymétrique, valeur 0, tout le monde à 1/3."""
    solution = solve_matrix([[0, -1, 1],
                             [1, 0, -1],
                             [-1, 1, 0]])

    assert solution.value == pytest.approx(0)
    assert list(solution.row) == pytest.approx([1 / 3] * 3)
    assert list(solution.column) == pytest.approx([1 / 3] * 3)


def test_a_saddle_point_is_found_without_the_linear_program(monkeypatch):
    """Au dernier round, presque toutes les matrices ont un point-selle : le LP (1,5 ms de frais fixes) est évité."""
    from src.core.ai import equilibrium
    monkeypatch.setattr(equilibrium, "linprog", lambda *args, **kwargs: pytest.fail("LP appelé sur un point-selle"))

    solution = solve_matrix([[1, 5, 2],
                             [3, 4, 6],
                             [0, 1, -1]])

    assert solution.value == pytest.approx(3)
    assert list(solution.row) == pytest.approx([0, 1, 0])
    assert list(solution.column) == pytest.approx([1, 0, 0])
