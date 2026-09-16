#!/usr/bin/env python3
"""
Mesure ce que vaut une IA entraînée, contre les adversaires de référence.

    .venv/bin/python scripts/evaluate_ai.py data/ai/heuristique.json
    .venv/bin/python scripts/evaluate_ai.py data/ai/a.json --versus data/ai/b.json --games 800

Important : l'évaluation joue sur des **parties fraîches**, jamais celles de l'entraînement. Une IA peut très
bien exceller sur les decks qu'elle a vus et s'effondrer sur les autres ; c'est ce test-ci qui le dit.

Comment lire le résultat :

* Le taux est donné avec sa **marge d'erreur**. « 52 % ± 4 % » ne veut pas dire mieux que 50 % : c'est
  indistinguable. Il faut plus de parties avant de conclure.
* Chaque paire de decks est jouée **deux fois, camps inversés**, pour que la chance au tirage ne décide pas.
* Repère : l'heuristique gagne environ 76 % contre le jeu aléatoire. C'est la barre à dépasser.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.repositories.card_repository import official_card_catalogue   # noqa: E402
from src.core.ai.arena import duel                                              # noqa: E402
from src.core.ai.engine_api import DeckPool                                     # noqa: E402
from src.core.ai.opponent import STRATEGIES                                     # noqa: E402
from src.core.ai.policy import LinearPolicy, policy_strategy                    # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("policy", help="fichier JSON de l'IA à évaluer.")
    parser.add_argument("--versus", help="évaluer contre une autre IA entraînée plutôt que contre les références.")
    parser.add_argument("--games", type=int, default=600, help="parties par affrontement (défaut : 600).")
    parser.add_argument("--seed", type=int, default=99, help="graine du hasard (différente de l'entraînement !).")
    parser.add_argument("--explain", action="store_true", help="afficher aussi les poids appris.")
    args = parser.parse_args()

    policy = LinearPolicy.load(args.policy)
    name = os.path.basename(args.policy)
    pool = DeckPool(official_card_catalogue())

    if policy.meta:
        print("Provenance de cette IA :")
        for key, value in policy.meta.items():
            print(f"  {key} : {value}")
        print()

    strategy = policy_strategy(policy)
    print(f"{args.games} parties par affrontement, decks tirés au hasard, camps inversés à chaque manche.\n")

    if args.versus:
        other = LinearPolicy.load(args.versus)
        result = duel(strategy, policy_strategy(other), pool, args.games, random.Random(args.seed))
        print(result.summary(name, os.path.basename(args.versus)))
    else:
        for opponent_name, opponent in (("aléatoire", STRATEGIES["random"]), ("heuristique", STRATEGIES["heuristic"])):
            result = duel(strategy, opponent, pool, args.games, random.Random(args.seed))
            print(result.summary(name, opponent_name))

        print("\nPour comparaison, les références entre elles :")
        reference = duel(STRATEGIES["heuristic"], STRATEGIES["random"], pool, args.games, random.Random(args.seed))
        print("  " + reference.summary("heuristique", "aléatoire"))

    if args.explain:
        print("\nCe que l'IA a appris :")
        print(policy.explain(top=10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
