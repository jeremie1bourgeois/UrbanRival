"""
Le conseil de Nash (scripts/conseil_nash.py) part de l'état du combat vu par le joueur conseillé : quand il est p1 du
serveur, l'enregistrement est retourné. Retourné, il doit donner le même état aux camps près, à chaque round.
"""
import glob
import json
import os

from scripts.conseil_nash import game_before, seen_by
from src.core.engine.contract import state_from_game

BATTLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ur_battles")


def _battle(name: str) -> dict:
    with open(os.path.join(BATTLES_DIR, name), encoding="utf-8") as file:
        return json.load(file)


def test_a_battle_seen_twice_from_the_other_side_is_unchanged():
    record = _battle("1181426.json")
    assert seen_by(seen_by(record, "p1"), "p1") == record


def test_the_other_side_sees_the_same_state_with_the_camps_swapped():
    for path in sorted(glob.glob(os.path.join(BATTLES_DIR, "*.json")))[:10]:
        record = _battle(os.path.basename(path))
        for round_number in range(1, len(record["rounds"]) + 1):
            p0_view = state_from_game(game_before(record, round_number))
            p1_view = state_from_game(game_before(seen_by(record, "p1"), round_number))
            assert (p1_view.nb_turn, p1_view.ally, p1_view.enemy) == (p0_view.nb_turn, p0_view.enemy, p0_view.ally), \
                f"{path}, round {round_number}"
