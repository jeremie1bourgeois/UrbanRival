"""
Éclate la sortie de urRecords() (scripts/ur_capture.js) en un fichier par combat dans data/ur_battles/, puis
rejoue chaque combat dans le moteur et affiche le premier écart avec le journal des effets.
Usage (depuis UrbanPy/Backend_fastAPI) : .venv/bin/python scripts/import_ur_battles.py records.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.use_cases.process_round import process_round  # noqa: E402
from src.schemas.game_schemas import ProcessRoundInput  # noqa: E402
from tests.test_ur_battles import _game  # noqa: E402

BATTLES_DIR = os.path.join(ROOT, "data", "ur_battles")


def replay(record: dict) -> str:
    """Rejoue le combat ; renvoie '' si le moteur reproduit tout, sinon la description du premier écart."""
    game = _game(record)
    for round_ in record["rounds"]:
        game.turn = round_["first"] == "p0"
        p0, p1 = round_["p0"], round_["p1"]
        process_round(game, ProcessRoundInput(player1_card_index=p0["index"], player1_pillz=p0["pillz"], player1_fury=p0["fury"],
                                              player2_card_index=p1["index"], player2_pillz=p1["pillz"], player2_fury=p1["fury"]))
        ally, enemy = game.ally.cards[p0["index"]], game.enemy.cards[p1["index"]]
        observed = {"p0": [ally.power_fight, ally.damage_fight, ally.attack, ally.win],
                    "p1": [enemy.power_fight, enemy.damage_fight, enemy.attack, enemy.win]}
        expected = {side: [round_[side][k] for k in ("power", "damage", "attack", "won")] for side in ("p0", "p1")}
        if observed != expected or (round_["after"]["life"] is not None and (
                [game.ally.life, game.enemy.life] != round_["after"]["life"] or [game.ally.pillz, game.enemy.pillz] != round_["after"]["pillz"])):
            log = "\n      ".join(entry["text"] for entry in game.history[-1].log)
            return (f"round {round_['round']} : attendu {expected} / vies {round_['after']['life']} pillz {round_['after']['pillz']}, "
                    f"obtenu {observed} / vies {[game.ally.life, game.enemy.life]} pillz {[game.ally.pillz, game.enemy.pillz]}\n      {log}")
    return ""


def main(path: str) -> None:
    with open(path, encoding="utf-8") as file:
        records = json.load(file)
    if isinstance(records, dict):
        records = [records]
    os.makedirs(BATTLES_DIR, exist_ok=True)
    for record in records:
        target = os.path.join(BATTLES_DIR, f"{record['battle_id']}.json")
        new = not os.path.exists(target)
        with open(target, "w", encoding="utf-8") as file:
            json.dump(record, file, indent=1, ensure_ascii=False)
        gap = replay(record)
        status = "OK  " if not gap else "ÉCART"
        print(f"{status} {record['battle_id']} ({'nouveau' if new else 'remplacé'}, {len(record['rounds'])} rounds) "
              f"{record['p0']['name']} vs {record['p1']['name']}" + (f"\n   {gap}" if gap else ""))


if __name__ == "__main__":
    main(sys.argv[1])
