#!/usr/bin/env python3
"""
Banc d'essai des adversaires automatiques : les fait s'affronter deux à deux et affiche leurs taux de victoire.

    python scripts/ai_arena.py                          # toutes les stratégies, 40 parties par affrontement
    python scripts/ai_arena.py --games 200 --seed 1
    python scripts/ai_arena.py greedy heuristic         # un seul affrontement

Les deux joueurs reçoivent la même main (deux clans à deux cartes, bonus actifs) et changent de côté d'une
partie à l'autre : ce qui est mesuré, ce sont les décisions. Un taux de victoire compte les nulles pour moitié.
"""
import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.ai import arena                                        # noqa: E402
from src.core.ai.opponent import STRATEGIES                          # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("strategies", nargs="*", default=[],
                        help=f"deux stratégies à opposer parmi {', '.join(sorted(STRATEGIES))} "
                             "(par défaut : toutes, deux à deux)")
    parser.add_argument("--games", type=int, default=40, help="parties par affrontement (défaut : 40)")
    parser.add_argument("--seed", type=int, default=0, help="graine du tirage des mains et des stratégies")
    args = parser.parse_args()

    unknown = [name for name in args.strategies if name not in STRATEGIES]
    if unknown:
        parser.error(f"stratégie inconnue : {', '.join(unknown)} (connues : {', '.join(sorted(STRATEGIES))})")

    rng = random.Random(args.seed)
    if len(args.strategies) == 2:
        first, second = args.strategies
        matches = {(first, second): arena.duel(STRATEGIES[first], STRATEGIES[second], args.games, rng)}
    elif args.strategies:
        parser.error("donner deux stratégies, ou aucune pour un tournoi complet")
    else:
        start = time.perf_counter()
        matches = arena.round_robin(STRATEGIES, args.games, rng)
        print(f"({time.perf_counter() - start:.1f} s)\n")

    width = max(len(first) for first, _ in matches)
    for (first, second), result in matches.items():
        print(f"{first:>{width}} contre {second:<{width}}  {result}")


if __name__ == "__main__":
    main()
