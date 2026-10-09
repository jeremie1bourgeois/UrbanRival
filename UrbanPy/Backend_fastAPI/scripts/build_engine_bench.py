"""
Banc d'essai du moteur Rust (docs/PLAN-MOTEUR.md, étape 3.1) : un lot fixe de paires de mains et, pour chacune,
l'état de début des rounds 1, 2, 3 et 4 d'une même partie. Les mains sont tirées comme pour les résolutions en masse
(src/core/engine/hands.py, de nuit une fois sur deux) ; chaque partie est jouée au hasard (coups tirés uniformément
parmi les coups légaux, rounds joués par le moteur Python de référence). Une partie finie avant le round 4 est
écartée. Les mesures d'une version à l'autre se font sur ce même lot (UrbanRust/examples/banc.rs).
Écrit data/engine_bench.json (versionné, une partie par ligne : identifiant, nuit, deck compilé, états de début des
rounds 1 à 4) ; graine fixe, à ne régénérer que pour changer de banc.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_engine_bench.py
"""
import json
import os
import random
import sys
from dataclasses import asdict
from typing import Iterator, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.domain.game import Game  # noqa: E402
from src.core.domain.player import Player  # noqa: E402
from src.core.engine.contract import Deck, State, deck_from_game, state_from_game  # noqa: E402
from src.core.engine.hands import random_hand  # noqa: E402
from src.core.engine.reference import legal_actions, step, terminal  # noqa: E402
from src.core.engine.scenarios import NIGHT_RATE  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

BENCH_PATH = os.path.join(BASE_DIR, "data", "engine_bench.json")
GAMES = 24
LAST_ROUND = 4
SEED = 3


def bench_games(count: int, seed: int) -> Iterator[Tuple[str, bool, Deck, List[State]]]:
    """(identifiant, nuit, deck, états de début des rounds 1 à LAST_ROUND) de parties jouées au hasard."""
    rng = random.Random(seed)
    number = found = 0
    while found < count:
        night = rng.random() < NIGHT_RATE
        game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [], night=night)
        game.ally.cards, game.enemy.cards = random_hand(rng, night), random_hand(rng, night)
        deck, state = deck_from_game(game), state_from_game(game)
        states = [state]
        while state.nb_turn < LAST_ROUND and terminal(state) is None:
            state = step(deck, state, rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy")))
            states.append(state)
        if terminal(state) is None:
            found += 1
            yield f"partie-{number}", night, deck, states
        number += 1


def main() -> None:
    lines = [
        json.dumps({"id": name, "night": night, "deck": asdict(deck), "states": [asdict(state) for state in states]},
                   ensure_ascii=False)
        for name, night, deck, states in bench_games(GAMES, SEED)
    ]
    with open(BENCH_PATH, "w", encoding="utf-8", newline="\n") as file:
        file.write("[\n" + ",\n".join(lines) + "\n]\n")
    print(f"{GAMES} parties, rounds 1 à {LAST_ROUND} -> {BENCH_PATH}")


if __name__ == "__main__":
    main()
