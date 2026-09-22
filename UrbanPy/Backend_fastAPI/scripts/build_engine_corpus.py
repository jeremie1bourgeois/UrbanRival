"""
Génère le corpus de non-régression du moteur (voir src/core/engine/corpus.py) : des parties jouées au hasard par le
moteur Python de référence, écrites en JSON sous la forme du contrat. Un moteur compilé doit reproduire chaque
entrée ; à relancer (même graine) après tout changement de règle pour mettre le corpus à jour.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_engine_corpus.py [--games 500] [--extra-pairs 4] [--seed 0] [--out data/engine_corpus/corpus.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine.corpus import build_corpus  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", type=int, default=500)
    parser.add_argument("--extra-pairs", type=int, default=4, help="paires d'actions non jouées enregistrées par état")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=os.path.join(BASE_DIR, "data", "engine_corpus", "corpus.json"))
    args = parser.parse_args()

    corpus = build_corpus(games=args.games, extra_pairs=args.extra_pairs, seed=args.seed)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as file:
        json.dump(corpus, file, ensure_ascii=False)

    states = sum(len(game["states"]) for game in corpus["games"])
    plays = sum(len(state["plays"]) for game in corpus["games"] for state in game["states"])
    print(f"{args.games} parties, {states} états, {plays} coups -> {args.out} ({os.path.getsize(args.out) / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
