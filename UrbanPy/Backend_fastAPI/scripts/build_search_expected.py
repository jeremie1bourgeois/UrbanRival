"""
Valeurs attendues de la recherche exacte du moteur Rust (docs/PLAN-MOTEUR.md, étapes 1.9 et 1.10) : la valeur exacte
d'états de rounds 4 et 3, calculée lentement par le moteur Python de référence (src/core/engine/reference.py) et SciPy,
selon docs/IA.md § 5.1 :

    V(état) vaut 1 / 0,5 / 0 si la partie est finie. Sinon, le premier joueur F choisit sa carte (publique), puis F
    mise et S choisit carte et mise sans voir la mise de F : pour chaque carte de F, un jeu matriciel (lignes = mises
    de F, colonnes = (carte, mise) de S, cases = V de l'état suivant, pour F) ; F prend la carte de meilleure valeur.
    V est rendue pour l'allié.

Les états viennent de parties jouées au hasard (scenarios.random_scenarios, graine fixe : la famille « aleatoire » du
corpus), sans doublon, pris à intervalle régulier ; s'y ajoutent les états du round 3 aux plus gros stocks de pillz,
et des « jumeaux » : des états du round 3 où les deux camps ont la même main, les mêmes cartes jouées, les mêmes vies
et pillz. Les mains aléatoires sont souvent si inégales que la valeur vaut 0, ½ ou 1 ; entre jumeaux, seuls le bluff
et l'avantage du premier joueur départagent, d'où des équilibres mixtes et des valeurs fractionnaires. Chaque valeur de
matrice est calculée par le programme des lignes et par celui des colonnes, qui doivent s'accorder.
Écrit data/search_expected.json (versionné, un état par ligne) : deck compilé, état, valeur pour l'allié, valeur de
chaque carte du premier joueur pour lui (null : carte déjà jouée), nombre d'états distincts résolus.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_search_expected.py
"""
import json
import os
import sys
import time
from dataclasses import asdict, replace
from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine.contract import Action, Deck, State  # noqa: E402
from src.core.engine.reference import legal_actions, step, terminal  # noqa: E402
from src.core.engine.scenarios import random_scenarios  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

EXPECTED_PATH = os.path.join(BASE_DIR, "data", "search_expected.json")
STATES_PER_ROUND = {4: 30, 3: 20}
RICH_STATES = 10   # états du round 3 aux plus gros stocks de pillz, en plus
TWIN_STATES = 8    # jumeaux du round 3, en plus
TWIN_STOCK = (9, 7)   # vies et pillz de chaque jumeau : assez de vies pour que le round 4 compte, assez de pillz pour bluffer
AGREEMENT = 1e-9   # écart toléré entre la valeur des lignes et celle des colonnes, et hors de [0, 1]


def solve_zero_sum(matrix: np.ndarray) -> float:
    """Valeur du jeu pour les lignes (qui maximisent) : le programme de docs/IA.md § 4.3."""
    rows, cols = matrix.shape
    objective = np.zeros(rows + 1)
    objective[-1] = -1                                              # linprog minimise : on minimise -v
    upper = np.hstack([-matrix.T, np.ones((cols, 1))])              # -Σ_i p_i M[i, j] + v <= 0
    equality = np.append(np.ones(rows), 0).reshape(1, -1)           # Σ p_i = 1
    result = linprog(objective, A_ub=upper, b_ub=np.zeros(cols), A_eq=equality, b_eq=[1],
                     bounds=[(0, 1)] * rows + [(None, None)])
    assert result.success, result.message
    return result.x[-1]


def game_value(matrix: np.ndarray) -> float:
    row_value, col_value = solve_zero_sum(matrix), solve_zero_sum(-matrix.T)
    assert abs(row_value + col_value) < AGREEMENT, (row_value, col_value)
    return row_value


class Search:
    """La récursion de docs/IA.md § 5.1 sur un deck, avec une mémo par état (State est hashable)."""

    def __init__(self, deck: Deck):
        self.deck = deck
        self.memo: Dict[State, float] = {}

    def value(self, state: State) -> float:
        """V(état) pour l'allié."""
        end = terminal(state)
        if end is not None:
            return end
        if state not in self.memo:
            best = max(value for value in self.card_values(state) if value is not None)
            self.memo[state] = best if state.ally_first else 1 - best
        return self.memo[state]

    def card_values(self, state: State) -> List[Optional[float]]:
        """Pour chaque carte de la main du premier joueur, la valeur pour lui de son jeu de mises ; None si jouée."""
        first, second = ("ally", "enemy") if state.ally_first else ("enemy", "ally")
        actions, replies = legal_actions(state, first), legal_actions(state, second)
        values: List[Optional[float]] = [None] * 4
        for card in sorted({action.card for action in actions}):
            bets = [action for action in actions if action.card == card]
            matrix = np.array([[self.for_first(state, bet, reply) for reply in replies] for bet in bets])
            values[card] = game_value(matrix)
        return values

    def for_first(self, state: State, action: Action, reply: Action) -> float:
        """V de l'état suivant, pour le premier joueur, qui joue `action` contre `reply`."""
        ally_action, enemy_action = (action, reply) if state.ally_first else (reply, action)
        value = self.value(step(self.deck, state, ally_action, enemy_action))
        return value if state.ally_first else 1 - value


def sample_states():
    """(nom, deck, état) : les états de rounds 4 et 3 des parties aléatoires, sans doublon, à intervalle régulier."""
    candidates = {round_number: [] for round_number in STATES_PER_ROUND}
    seen = set()
    for scenario in random_scenarios():
        state = scenario.state
        if state.nb_turn in candidates and (scenario.deck, state) not in seen:
            seen.add((scenario.deck, state))
            name = scenario.label.rsplit("/coup-", 1)[0]
            candidates[state.nb_turn].append((name, scenario.deck, state))
    selected = []
    for round_number, states in candidates.items():
        stride = max(1, len(states) // STATES_PER_ROUND[round_number])
        selected += states[::stride][:STATES_PER_ROUND[round_number]]
    richest = sorted(candidates[3], key=lambda item: -min(item[2].ally.pillz, item[2].enemy.pillz))
    selected += [item for item in richest if item not in selected][:RICH_STATES]
    selected += [twins(*item) for item in selected if item[2].nb_turn == 3][:TWIN_STATES]
    return selected


def twins(name: str, deck: Deck, state: State):
    """L'état où les deux camps sont l'allié : sa main, ses cartes jouées et ses effets, les vies et pillz de TWIN_STOCK."""
    life, pillz = TWIN_STOCK
    player = replace(state.ally, life=life, pillz=pillz)
    last_round = None if state.last_round is None else (state.last_round[0], state.last_round[0], state.last_round[2])
    twin_deck = Deck(ally=deck.ally, enemy=deck.ally, ally_start=deck.ally_start, enemy_start=deck.ally_start)
    return f"{name}/jumeaux", twin_deck, replace(state, ally=player, enemy=player, last_round=last_round)


def solve(item) -> dict:
    name, deck, state = item
    search = Search(deck)
    start = time.perf_counter()
    card_values = [value if value is None else value + 0.0 for value in search.card_values(state)]
    best = max(value for value in card_values if value is not None)
    value = (best if state.ally_first else 1 - best) + 0.0   # + 0.0 : pas de -0.0 dans le fichier
    assert -AGREEMENT <= value <= 1 + AGREEMENT, (name, value)
    entry = {"name": name, "deck": asdict(deck), "state": asdict(state), "value": value,
             "card_values": card_values, "states": len(search.memo) + 1}
    return entry, time.perf_counter() - start


def main() -> None:
    items = sample_states()
    results = []
    for number, item in enumerate(items, 1):
        results.append(solve(item))
        print(f"{number}/{len(items)} {item[0]} : {results[-1][1]:.1f} s", flush=True)
    for round_number in STATES_PER_ROUND:
        timings = [(entry["states"], seconds) for entry, seconds in results if entry["state"]["nb_turn"] == round_number]
        print(f"round {round_number} : {len(timings)} états, {sum(n for n, _ in timings) / len(timings):.0f} états "
              f"résolus en moyenne, {sum(s for _, s in timings) / len(timings):.1f} s en moyenne")
    with open(EXPECTED_PATH, "w", encoding="utf-8", newline="\n") as file:
        file.write("[\n" + ",\n".join(json.dumps(entry) for entry, _ in results) + "\n]\n")
    print(f"{len(results)} états -> {EXPECTED_PATH}")


if __name__ == "__main__":
    main()
