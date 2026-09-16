#!/usr/bin/env python3
"""
Entraîne l'IA et enregistre le résultat dans un fichier JSON lisible.

Exemples :

    # un premier essai rapide (~1 min) pour vérifier que tout tourne
    .venv/bin/python scripts/train_ai.py --generations 10 --population 20 --games 40

    # un entraînement sérieux contre l'heuristique (~10 min)
    .venv/bin/python scripts/train_ai.py --generations 40 --population 40 --games 80 \
        --opponent heuristic --out data/ai/heuristique.json

    # auto-apprentissage : l'IA affronte sa propre version courante
    .venv/bin/python scripts/train_ai.py --opponent self --generations 40 --out data/ai/selfplay.json

Tout est reproductible : à `--seed` égale, le même entraînement redonne exactement le même résultat.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.repositories.card_repository import official_card_catalogue   # noqa: E402
from src.core.ai.engine_api import DeckPool                                     # noqa: E402
from src.core.ai.train import TrainingConfig, train                             # noqa: E402
from src.utils.config import BASE_DIR                                           # noqa: E402

DEFAULT_OUT = os.path.join(BASE_DIR, "data", "ai", "policy.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--generations", type=int, default=20,
                        help="nombre de tours d'amélioration (défaut : 20). Plus = mieux, mais plus long.")
    parser.add_argument("--population", type=int, default=30,
                        help="candidats testés par génération (défaut : 30). Plus = recherche plus large.")
    parser.add_argument("--games", type=int, default=60,
                        help="parties jouées pour noter chaque candidat (défaut : 60). Plus = note plus fiable.")
    parser.add_argument("--elite-fraction", type=float, default=0.25,
                        help="part des candidats conservés à chaque génération (défaut : 0.25).")
    parser.add_argument("--opponent", default="heuristic", choices=["random", "heuristic", "self"],
                        help="adversaire d'entraînement (défaut : heuristic).")
    parser.add_argument("--spread", type=float, default=0.5,
                        help="dispersion du tirage initial des poids (défaut : 0.5).")
    parser.add_argument("--seed", type=int, default=0, help="graine du hasard : même graine = même résultat.")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"fichier de sortie (défaut : {DEFAULT_OUT}).")
    parser.add_argument("--all-cards", action="store_true",
                        help="entraîner aussi sur les cartes dont le moteur ne gère pas le pouvoir "
                             "(déconseillé : l'IA apprendrait sur des règles fausses).")
    args = parser.parse_args()

    config = TrainingConfig(
        generations=args.generations,
        population=args.population,
        elite_fraction=args.elite_fraction,
        games_per_candidate=args.games,
        opponent=args.opponent,
        initial_spread=args.spread,
        seed=args.seed,
        only_supported_cards=not args.all_cards,
    )

    print(config.describe())
    pool = DeckPool(official_card_catalogue(), only_supported=config.only_supported_cards)
    print(f"{len(pool.entries)} cartes utilisables pour composer les decks\n")
    print("Lecture des colonnes : « meilleur » = le meilleur candidat de la génération, « moyenne » = tous les")
    print("candidats, « exploration » = à quel point la recherche cherche encore loin (elle baisse en se fixant).")
    print("Attention : les decks changent à chaque génération, donc la courbe monte en dents de scie.\n")

    started = time.perf_counter()
    policy, reports = train(config, pool=pool, on_generation=lambda report: print(report.line(), flush=True))
    elapsed = time.perf_counter() - started

    policy.meta["secondes"] = round(elapsed, 1)
    policy.save(args.out)

    print(f"\nTerminé en {elapsed:.0f} s. IA enregistrée dans {args.out}")
    print("\nCe que l'IA a appris (les critères qui pèsent le plus) :")
    print(policy.explain(top=8))
    print("\nÉtape suivante — mesurer ce que ça vaut vraiment, sur des parties fraîches :")
    print(f"  .venv/bin/python scripts/evaluate_ai.py {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
