"""
Équilibre de Nash d'un jeu matriciel à somme nulle, par programmation linéaire (`scipy.optimize.linprog`, HiGHS).

Convention : la ligne maximise, la colonne minimise, `matrix[i][j]` est le gain de la ligne. Le solveur
(`src/core/ai/solver.py`) ne demande rien d'autre : un round se résout par carte du premier joueur, en jeux
matriciels indépendants (voir docs/IA.md, « Un round se résout par carte »).
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class Equilibrium:
    """Valeur du jeu (pour la ligne) et stratégies mixtes optimales des deux joueurs."""
    value: float
    row: np.ndarray
    column: np.ndarray


def solve_matrix(matrix) -> Equilibrium:
    """
    Stratégie maximin de la ligne, minimax de la colonne, et valeur du jeu — en un seul programme linéaire :
        max v  sous  Σ_i x_i · payoff[i][j] ≥ v pour toute colonne j,  Σ x_i = 1,  x ≥ 0.
    Variables (x_1..x_n, v) ; linprog minimise, donc on minimise -v. La stratégie de la colonne est le dual des
    contraintes « par colonne » (une seconde résolution coûterait autant que la première : ~1,5 ms de frais fixes).
    """
    payoff = np.asarray(matrix, dtype=float)
    n_rows, n_cols = payoff.shape
    objective = np.zeros(n_rows + 1)
    objective[-1] = -1
    inequalities = np.hstack([-payoff.T, np.ones((n_cols, 1))])       # v - Σ x_i payoff[i][j] ≤ 0
    equality = np.append(np.ones(n_rows), 0).reshape(1, -1)           # Σ x_i = 1
    bounds = [(0, None)] * n_rows + [(None, None)]
    result = linprog(objective, A_ub=inequalities, b_ub=np.zeros(n_cols), A_eq=equality, b_eq=[1],
                     bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"LP failed: {result.message}")
    column = np.clip(-result.ineqlin.marginals, 0, None)
    return Equilibrium(value=-result.fun, row=result.x[:-1], column=column / column.sum())
