"""
Génère le corpus de non-régression du moteur (voir src/core/engine/corpus.py) : chaque famille de scénarios
(src/core/engine/scenarios.py) jouée par le moteur Python de référence, écrite en JSONL sous la forme du contrat,
et met à jour les digests versionnés (data/engine_digests.json). Un moteur compilé doit reproduire chaque entrée ;
à relancer après tout changement de règle pour mettre le corpus et les digests à jour.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_engine_corpus.py [--family solo --family combat ...] [--out data/engine_corpus]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine.corpus import write_corpus  # noqa: E402
from src.core.engine.scenarios import FAMILIES  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

CORPUS_DIR = os.path.join(BASE_DIR, "data", "engine_corpus")
DIGESTS_PATH = os.path.join(BASE_DIR, "data", "engine_digests.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", action="append", choices=list(FAMILIES), help="famille à (ré)écrire ; défaut : toutes")
    parser.add_argument("--out", default=CORPUS_DIR)
    args = parser.parse_args()

    start = time.perf_counter()
    digests = write_corpus(args.out, DIGESTS_PATH, args.family)
    for name, summary in digests["families"].items():
        if args.family and name not in args.family:
            continue
        size = os.path.getsize(os.path.join(args.out, f"{name}.jsonl")) / 1e6
        print(f"{name:14s} {summary['entries']:7d} entrées  {summary['decks']:6d} decks  {size:6.1f} Mo  {summary['sha256'][:12]}")
    print(f"-> {args.out} en {time.perf_counter() - start:.0f} s ; digests dans {DIGESTS_PATH}")


if __name__ == "__main__":
    main()
