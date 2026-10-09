"""
Valeurs attendues du solveur de matrices du moteur Rust (UrbanRust/src/nash.rs ; docs/PLAN-MOTEUR.md, étape 1.6) :
des matrices de jeu à somme nulle tirées au hasard (graine fixe), aux tailles d'un bloc de mises et de la matrice du
premier joueur, résolues par SciPy (linprog, HiGHS) comme dans docs/IA.md § 4.3. Chaque valeur est calculée deux fois,
par le programme des lignes et par celui des colonnes, qui doivent s'accorder.
Écrit data/nash_expected.json (versionné, une matrice par ligne) ; à relancer seulement pour changer les matrices.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_nash_expected.py
"""
import json
import os
import random
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import BASE_DIR  # noqa: E402

EXPECTED_PATH = os.path.join(BASE_DIR, "data", "nash_expected.json")
SEED = 0
AGREEMENT = 1e-9   # écart toléré entre la valeur des lignes et celle des colonnes

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


def matrices(rng: random.Random):
    for rows, cols in SHAPES:
        for kind, draw in VALUES.items():
            for number in range(1 if rows * cols > LARGE else 3):
                values = [draw(rng) for _ in range(rows * cols)]
                yield {"name": f"{rows}x{cols}/{kind}/{number}", "rows": rows, "cols": cols, "values": values}


def main() -> None:
    entries = []
    for entry in matrices(random.Random(SEED)):
        entry["value"] = game_value(np.array(entry["values"]).reshape(entry["rows"], entry["cols"]))
        entries.append(entry)
    with open(EXPECTED_PATH, "w", encoding="utf-8", newline="\n") as file:
        file.write("[\n" + ",\n".join(json.dumps(entry) for entry in entries) + "\n]\n")
    print(f"{len(entries)} matrices -> {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
