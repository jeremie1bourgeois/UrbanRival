"""
Rapport de couverture du parseur de capacités sur les descriptions officielles.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/capacity_coverage.py
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.repositories.card_repository import all_capacity_descriptions  # noqa: E402
from src.core.parsing.capacity_parser import parse_capacity  # noqa: E402


def main() -> None:
    descriptions = sorted(all_capacity_descriptions())
    results = {text: parse_capacity(text) for text in descriptions}
    supported = [text for text, result in results.items() if result.supported]
    unsupported = defaultdict(list)
    for text, result in results.items():
        if not result.supported:
            unsupported[result.reason].append(text)

    print(f"{len(supported)}/{len(descriptions)} descriptions supportées ({100 * len(supported) / len(descriptions):.1f} %)")
    print(f"{len(descriptions) - len(supported)} non supportées, par raison :")
    for reason, count in Counter({reason: len(texts) for reason, texts in unsupported.items()}).most_common():
        print(f"\n[{count}] {reason}")
        for text in sorted(unsupported[reason]):
            print(f"    {text}")


if __name__ == "__main__":
    main()
