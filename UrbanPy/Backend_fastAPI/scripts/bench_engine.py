#!/usr/bin/env python3
"""
Débit de l'API moteur (feuille de route D3) : l'apprentissage par renforcement joue des millions de rounds,
il faut savoir combien il en coûte un.

    python scripts/bench_engine.py                # ~2 s par mesure
    python scripts/bench_engine.py --seconds 5

Mesure, sur des mains tirées au hasard : la copie d'un état, un round avec et sans journal des effets, une
partie complète jouée au hasard, le coût d'une décision de chaque stratégie au round 1, et celui du solveur
exact sur les rounds qu'il résout (cache vidé avant chaque mesure : c'est le coût d'une fin de partie inédite).
"""
import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.ai import arena, engine, solver                        # noqa: E402
from src.core.ai.opponent import STRATEGIES                          # noqa: E402
from src.core.domain.game import NB_ROUNDS                           # noqa: E402


def measure(label: str, action, seconds: float, unit: str = "appels") -> None:
    """Répète `action` pendant `seconds` et affiche le débit obtenu."""
    count, start = 0, time.perf_counter()
    while time.perf_counter() - start < seconds:
        action()
        count += 1
    elapsed = time.perf_counter() - start
    print(f"{label:<34} {count / elapsed:>9.0f} {unit}/s   ({1000 * elapsed / count:.2f} ms)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=float, default=2.0, help="durée de chaque mesure (défaut : 2 s)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    hands = arena.mirrored_hands(rng)
    fresh = engine.new_game(*hands)

    measure("new_game (cartes officielles)", lambda: engine.new_game(*hands), args.seconds, "parties")
    measure("clone", lambda: engine.clone(fresh), args.seconds, "copies")

    first_pick, second_pick = engine.Pick(0, 3), engine.Pick(1, 2)
    measure("step (journal compris)", lambda: engine.step(fresh, first_pick, second_pick), args.seconds, "rounds")
    measure("step (sans journal)", lambda: engine.step(fresh, first_pick, second_pick, log=False), args.seconds, "rounds")

    random_strategies = {"ally": STRATEGIES["random"], "enemy": STRATEGIES["random"]}
    measure("partie complète (aléatoire)", lambda: engine.play_out(fresh, random_strategies, rng), args.seconds, "parties")

    for name, strategy in STRATEGIES.items():
        measure(f"décision « {name} » (round 1)", lambda strategy=strategy: strategy(fresh, "ally", rng),
                args.seconds, "décisions")

    for round_number, pillz in ((NB_ROUNDS, 12), (NB_ROUNDS - 1, 6)):
        state = endgame(fresh, round_number, pillz)
        measure(f"solveur exact (round {round_number}, {pillz} pillz)",
                lambda state=state: (solver.clear_cache(), solver.solve(state)), args.seconds, "résolutions")


def endgame(game, round_number: int, pillz: int):
    """La partie amenée au round demandé : premières cartes jouées, `pillz` restantes de chaque côté."""
    state = engine.clone(game)
    state.nb_turn = round_number
    state.ally.pillz = state.enemy.pillz = pillz
    for cards in (state.ally.cards, state.enemy.cards):
        for index, card in enumerate(cards):
            card.played = index < round_number - 1
    return state


if __name__ == "__main__":
    main()
