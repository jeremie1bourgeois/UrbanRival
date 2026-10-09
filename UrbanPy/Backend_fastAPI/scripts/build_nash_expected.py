"""
Valeurs attendues du solveur de matrices du moteur Rust (UrbanRust/src/nash.rs ; docs/PLAN-MOTEUR.md, étape 1.6) :
des matrices de jeu à somme nulle tirées au hasard (graine fixe), aux tailles d'un bloc de mises et de la matrice du
premier joueur, résolues par SciPy (linprog, HiGHS) comme dans docs/IA.md § 4.3. Chaque valeur est calculée deux fois,
par le programme des lignes et par celui des colonnes, qui doivent s'accorder. Pour chaque coup de chaque joueur, la
plus forte probabilité qu'il reçoive dans une stratégie optimale (étape 1.7) : un programme linéaire par coup. Sur
les petites matrices, les coins de l'ensemble des stratégies optimales de chaque joueur (étape 1.8), par force brute.
S'y ajoutent les matrices réelles de data/nash_real_matrices.json : des matrices du moteur sur lesquelles le solveur
Rust s'est trompé, gardées comme cas de test (étape 2.4).
Écrit data/nash_expected.json (versionné, une matrice par ligne) ; à relancer seulement pour changer les matrices.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_nash_expected.py
"""
import itertools
import json
import math
import os
import random
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import BASE_DIR  # noqa: E402

EXPECTED_PATH = os.path.join(BASE_DIR, "data", "nash_expected.json")
REAL_MATRICES_PATH = os.path.join(BASE_DIR, "data", "nash_real_matrices.json")
SEED = 0
AGREEMENT = 1e-9   # écart toléré entre la valeur des lignes et celle des colonnes
FEASIBILITY = 1e-9  # écart toléré sur une contrainte, et entre deux coins pour les confondre
BRUTE_FORCE_LIMIT = 5000   # au-delà de ce nombre de choix de contraintes saturées, pas de coins

# (lignes, colonnes) : de la matrice 1 × 1 au bloc de mises 23 × 23 et à la matrice du premier joueur 23 × 92
SHAPES = ((1, 1), (1, 5), (5, 1), (2, 2), (3, 3), (4, 4), (5, 7), (7, 5), (10, 10), (13, 23), (23, 23), (23, 46),
          (23, 69), (23, 92))
LARGE = 500   # au-delà de ce nombre de cases, une seule matrice par sorte de valeurs
# Sortes de valeurs : quelconques, ou à nombreuses égalités (fin de partie : perdu, nul, gagné), d'où des points-selles
# et des programmes dégénérés
VALUES = {
    "quelconques": lambda rng: round(rng.random(), 3),
    "trois-valeurs": lambda rng: rng.choice((0.0, 0.5, 1.0)),
    "quarts": lambda rng: rng.choice((0.0, 0.25, 0.5, 0.75, 1.0)),
}


def solve_zero_sum(matrix: np.ndarray):
    """Politique mixte des lignes (qui maximisent) et valeur du jeu : le programme de docs/IA.md § 4.3."""
    rows, cols = matrix.shape
    objective = np.zeros(rows + 1)
    objective[-1] = -1                                              # linprog minimise : on minimise -v
    upper = np.hstack([-matrix.T, np.ones((cols, 1))])              # -Σ_i p_i M[i, j] + v <= 0
    equality = np.append(np.ones(rows), 0).reshape(1, -1)           # Σ p_i = 1
    result = linprog(objective, A_ub=upper, b_ub=np.zeros(cols), A_eq=equality, b_eq=[1],
                     bounds=[(0, 1)] * rows + [(None, None)])
    assert result.success, result.message
    return result.x[:rows], result.x[-1]


def game_value(matrix: np.ndarray) -> float:
    _, row_value = solve_zero_sum(matrix)
    _, col_value = solve_zero_sum(-matrix.T)                         # le jeu vu des colonnes
    assert abs(row_value + col_value) < AGREEMENT, (row_value, col_value)
    return row_value


def best_probability(index: int, size: int, upper: np.ndarray, bound: float) -> float:
    """La plus forte probabilité du coup `index` parmi les stratégies (de `size` coups) qui vérifient upper · x <= bound."""
    objective = np.zeros(size)
    objective[index] = -1
    result = linprog(objective, A_ub=upper, b_ub=np.full(upper.shape[0], bound), A_eq=np.ones((1, size)), b_eq=[1],
                     bounds=[(0, 1)] * size)
    assert result.success, result.message
    return result.x[index]


def best_probabilities(matrix: np.ndarray, value: float):
    """Pour chaque ligne, sa plus forte probabilité dans une stratégie optimale des lignes (pᵀ M >= valeur) ; de même
    pour chaque colonne (M q <= valeur)."""
    rows, cols = matrix.shape
    row_best = [best_probability(row, rows, -matrix.T, -value) for row in range(rows)]
    col_best = [best_probability(col, cols, matrix, value) for col in range(cols)]
    return row_best, col_best


def corners(upper: np.ndarray, bound: float):
    """
    Les coins (sommets) de {x >= 0, Σ x = 1, upper · x <= bound}, par force brute : un sommet est un point admissible où
    n contraintes linéairement indépendantes sont saturées, Σ x = 1 comprise. Chaque choix de n - 1 inégalités (parmi
    upper · x <= bound et -x <= 0) donne au plus un point ; on garde les points admissibles, sans doublon. None si les
    choix sont trop nombreux.
    """
    size = upper.shape[1]
    inequalities = np.vstack([upper, -np.eye(size)])
    limits = np.concatenate([np.full(upper.shape[0], bound), np.zeros(size)])
    if math.comb(len(inequalities), size - 1) > BRUTE_FORCE_LIMIT:
        return None
    found = []
    for active in itertools.combinations(range(len(inequalities)), size - 1):
        system = np.vstack([inequalities[list(active)], np.ones(size)])
        if abs(np.linalg.det(system)) < 1e-12:
            continue
        point = np.linalg.solve(system, np.append(limits[list(active)], 1))
        admissible = np.all(inequalities @ point <= limits + FEASIBILITY)
        if admissible and not any(np.max(np.abs(point - other)) <= FEASIBILITY for other in found):
            found.append(point)
    return sorted(np.clip(point, 0, None).tolist() for point in found)


def matrices(rng: random.Random):
    for rows, cols in SHAPES:
        for kind, draw in VALUES.items():
            for number in range(1 if rows * cols > LARGE else 3):
                values = [draw(rng) for _ in range(rows * cols)]
                yield {"name": f"{rows}x{cols}/{kind}/{number}", "rows": rows, "cols": cols, "values": values}
    with open(REAL_MATRICES_PATH, encoding="utf-8") as file:
        yield from json.load(file)


def main() -> None:
    entries = []
    for entry in matrices(random.Random(SEED)):
        matrix = np.array(entry["values"]).reshape(entry["rows"], entry["cols"])
        entry["value"] = game_value(matrix)
        entry["row_best"], entry["col_best"] = best_probabilities(matrix, entry["value"])
        row_corners, col_corners = corners(-matrix.T, -entry["value"]), corners(matrix, entry["value"])
        if row_corners is not None and col_corners is not None:
            entry["row_corners"], entry["col_corners"] = row_corners, col_corners
        entries.append(entry)
    with open(EXPECTED_PATH, "w", encoding="utf-8", newline="\n") as file:
        file.write("[\n" + ",\n".join(json.dumps(entry) for entry in entries) + "\n]\n")
    print(f"{len(entries)} matrices -> {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
