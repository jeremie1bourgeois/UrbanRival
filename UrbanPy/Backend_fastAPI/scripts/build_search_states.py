"""
États de départ des résolutions en masse du moteur Rust (docs/PLAN-MOTEUR.md, étape 2.3) : 10 000 états du début du
round 3, chacun issu d'une partie jouée au hasard (mains de src/core/engine/hands.py, de nuit une fois sur deux, coups
tirés uniformément parmi les coups légaux, deux rounds joués par le moteur Python de référence). Une partie finie avant
le round 3 est écartée. Le moteur Rust résout chaque état sous ses contrôles (UrbanRust/tests/resolutions.rs).
Écrit data/engine_corpus/search_states.jsonl (non versionné, comme le corpus ; graine fixe, il se régénère à
l'identique) : une ligne par état, son identifiant, son deck compilé et l'état.
Usage (depuis UrbanPy/Backend_fastAPI) :
    python scripts/build_search_states.py
"""
import json
import os
import random
import sys
import time
from dataclasses import asdict
from typing import Iterator, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.domain.game import Game  # noqa: E402
from src.core.domain.player import Player  # noqa: E402
from src.core.engine.contract import Deck, State, deck_from_game, state_from_game  # noqa: E402
from src.core.engine.hands import random_hand  # noqa: E402
from src.core.engine.reference import legal_actions, step, terminal  # noqa: E402
from src.core.engine.scenarios import NIGHT_RATE  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

STATES_PATH = os.path.join(BASE_DIR, "data", "engine_corpus", "search_states.jsonl")
STATES = 10_000
START_ROUND = 3
SEED = 2


def start_states(count: int, seed: int) -> Iterator[Tuple[str, Deck, State]]:
    """(identifiant, deck, état) : le début du round START_ROUND de parties jouées au hasard."""
    rng = random.Random(seed)
    number = found = 0
    while found < count:
        night = rng.random() < NIGHT_RATE
        game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [], night=night)
        game.ally.cards, game.enemy.cards = random_hand(rng, night), random_hand(rng, night)
        deck, state = deck_from_game(game), state_from_game(game)
        while state.nb_turn < START_ROUND and terminal(state) is None:
            state = step(deck, state, rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy")))
        if terminal(state) is None:
            found += 1
            yield f"partie-{number}", deck, state
        number += 1


def main() -> None:
    start = time.perf_counter()
    os.makedirs(os.path.dirname(STATES_PATH), exist_ok=True)
    with open(STATES_PATH, "w", encoding="utf-8", newline="\n") as file:
        for name, deck, state in start_states(STATES, SEED):
            file.write(json.dumps({"id": name, "deck": asdict(deck), "state": asdict(state)}, ensure_ascii=False) + "\n")
    print(f"{STATES} états du round {START_ROUND} -> {STATES_PATH} en {time.perf_counter() - start:.0f} s")


if __name__ == "__main__":
    main()
