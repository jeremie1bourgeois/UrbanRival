"""
Conseil de Nash pendant un combat Urban Rivals : à chaque décision, la stratégie d'équilibre exacte pour le reste de
la partie, calculée par le moteur Rust (UrbanRust/examples/conseil.rs).

En direct (depuis UrbanPy/Backend_fastAPI) :
    .venv/bin/python scripts/conseil_nash.py --moi "jere'm"
puis, dans la console du client web où scripts/ur_capture.js est collé, `urConseil()` : chaque nouvel état du combat
est envoyé à ce script (http://127.0.0.1:8765), qui affiche le conseil dès que c'est à vous de jouer — tout de suite
si vous jouez en premier, sinon quand l'adversaire a posé sa carte.

Sur un combat enregistré (pour vérifier sans jouer) :
    .venv/bin/python scripts/conseil_nash.py --moi "jere'm" --rejouer data/ur_battles/1181426.json

Avant chaque conseil, les rounds déjà joués sont rejoués par le moteur Python et comparés aux valeurs du serveur
(scripts/import_ur_battles.py) : un écart est signalé, car le conseil part alors d'un état faux.
"""
import argparse
import json
import os
import queue
import random
import subprocess
import sys
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.import_ur_battles import replay  # noqa: E402
from src.core.engine.contract import Deck, deck_from_game, state_from_game  # noqa: E402
from src.core.use_cases.process_round import process_round  # noqa: E402
from src.schemas.game_schemas import ProcessRoundInput  # noqa: E402
from tests.test_ur_battles import _game  # noqa: E402

RUST_DIR = os.path.join(ROOT, "..", "..", "UrbanRust")
ADVICE_BINARY = os.path.join(RUST_DIR, "target", "release", "examples", "conseil")
PORT = 8765


# --- Le combat vu par le joueur conseillé -------------------------------------------------------

def seen_by(record: dict, side: str) -> dict:
    """L'enregistrement du combat (format de data/ur_battles) avec `side` en p0, l'allié du moteur."""
    if side == "p0":
        return record
    swap = {"p0": "p1", "p1": "p0"}
    rounds = [{**round_, "first": swap[round_["first"]], "p0": round_["p1"], "p1": round_["p0"],
               "post_round": round_["post_round"][::-1],
               "before": {key: values[::-1] for key, values in round_["before"].items()},
               "after": {key: values and values[::-1] for key, values in round_["after"].items()}}
              for round_ in record["rounds"]]
    return {**record, "p0": record["p1"], "p1": record["p0"], "rounds": rounds}


def game_before(record: dict, round_number: int):
    """La partie au début du round `round_number` (1 à 4), les rounds précédents rejoués avec les choix du combat."""
    game = _game(record)
    for round_ in record["rounds"][:round_number - 1]:
        game.turn = round_["first"] == "p0"
        p0, p1 = round_["p0"], round_["p1"]
        process_round(game, ProcessRoundInput(player1_card_index=p0["index"], player1_pillz=p0["pillz"], player1_fury=p0["fury"],
                                              player2_card_index=p1["index"], player2_pillz=p1["pillz"], player2_fury=p1["fury"]))
    return game


# --- Le moteur Rust -----------------------------------------------------------------------------

def build_engine() -> None:
    subprocess.run(["cargo", "build", "--release", "--example", "conseil"], cwd=RUST_DIR, check=True)


def ask_engine(deck: Deck, state, enemy_card: Optional[int]) -> dict:
    request = json.dumps({"deck": asdict(deck), "state": asdict(state), "enemy_card": enemy_card})
    answer = subprocess.run([ADVICE_BINARY], input=request, capture_output=True, text=True, check=True)
    return json.loads(answer.stdout)


# --- Le conseil ---------------------------------------------------------------------------------

def move_text(names, move: dict) -> str:
    """Un coup tel qu'on le joue dans le client : la carte, les pillz ajoutées (sans la gratuite), la fury."""
    return f"{names[move['card']]}, {move['pillz'] - 1} pillz" + (" + fury" if move["fury"] else "")


def advise(record: dict, round_number: int, enemy_card: Optional[int]) -> str:
    """Le conseil du round `round_number` pour p0 ; `enemy_card` : la carte posée par p1 s'il joue en premier."""
    game = game_before(record, round_number)
    game.turn = enemy_card is None
    try:
        deck = deck_from_game(game)
    except ValueError as error:   # pouvoir non géré : le moteur jouerait la carte sans lui
        return f"Pas de conseil : {error}"
    answer = ask_engine(deck, state_from_game(game), enemy_card)
    names = [card.name for card in deck.ally]
    lines = [f"Round {round_number} — valeur de la position : {answer['value']:.1%} "
             f"({answer['states']} états résolus en {answer['seconds']:.2f} s)"]
    if answer["cards"] is None:
        lines.append(f"  L'adversaire a posé {deck.enemy[enemy_card].name}.")
    else:
        lines.append("  Vous jouez en premier ; valeur de chaque carte : "
                     + " · ".join(f"{names[card['card']]} {card['value']:.1%}"
                                  for card in sorted(answer["cards"], key=lambda card: -card["value"])))
    strategy = sorted(answer["strategy"], key=lambda move: -move["probability"])
    for move in strategy:
        lines.append(f"    {move['probability']:6.1%}  {move_text(names, move)}")
    if len(strategy) > 1:
        draw = random.choices(strategy, weights=[move["probability"] for move in strategy])[0]
        lines.append(f"  Tirage selon ces probabilités : {move_text(names, draw)}")
    return "\n".join(lines)


def warn_if_engine_differs(record: dict) -> None:
    gap = replay(record)
    if gap:
        print(f"  ATTENTION, le moteur s'écarte du serveur sur un round déjà joué : {gap}")


# --- Combat enregistré --------------------------------------------------------------------------

def replay_battle(path: str, me: str) -> None:
    with open(path, encoding="utf-8") as file:
        record = json.load(file)
    side = side_of(record, me)
    record = seen_by(record, side)
    print(f"Combat {record['battle_id']} : {record['p0']['name']} contre {record['p1']['name']}")
    warn_if_engine_differs(record)
    names = [card.name for card in _game(record).ally.cards]
    for round_ in record["rounds"]:
        enemy_card = round_["p1"]["index"] if round_["first"] == "p1" else None
        print(advise(record, round_["round"], enemy_card))
        print(f"  Joué : {move_text(names, {'card': round_['p0']['index'], 'pillz': round_['p0']['pillz'], 'fury': round_['p0']['fury']})}\n")


def side_of(record: dict, me: str) -> str:
    for side in ("p0", "p1"):
        if record[side]["name"] == me:
            return side
    raise SystemExit(f"{me!r} ne joue pas ce combat ({record['p0']['name']} contre {record['p1']['name']}) : voir --moi")


# --- En direct ----------------------------------------------------------------------------------

class StatusHandler(BaseHTTPRequestHandler):
    """Reçoit les états envoyés par urConseil() (scripts/ur_capture.js) : {record, first, status}."""

    def do_OPTIONS(self) -> None:
        self._reply()

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.headers.get("Origin", "").endswith("urban-rivals.com"):
            self.server.statuses.put(json.loads(body))
        self._reply()

    def _reply(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def log_message(self, *args) -> None:
        pass


def latest(statuses: queue.Queue) -> dict:
    """Le dernier état reçu : chacun porte tout le combat, les précédents n'apprennent rien de plus."""
    payload = statuses.get()
    while not statuses.empty():
        payload = statuses.get()
    return payload


def on_status(payload: dict, me: str, advised: set) -> None:
    status, record = payload["status"], payload["record"]
    if status["status"] != "playing":
        return
    players = {"p0": status["player0"], "p1": status["player1"]}
    side = next((side for side, player in players.items() if player["player"]["name"] == me), None)
    if side is None:
        if status["id"] not in advised:
            advised.add(status["id"])
            print(f"{me!r} ne joue pas le combat {status['id']} : voir --moi")
        return
    round_index = status["round"]
    mine, theirs = players[side], players["p1" if side == "p0" else "p0"]
    if any(card["roundPlayed"] == round_index for card in mine["characters"]):
        return
    enemy_card = next((card["index"] for card in theirs["characters"] if card["roundPlayed"] == round_index), None)
    if payload["first"] != side and enemy_card is None:
        return   # l'adversaire joue en premier et n'a pas encore posé sa carte
    key = (status["id"], round_index, enemy_card)
    if key in advised:
        return
    advised.add(key)
    if len(record["rounds"]) != round_index:
        print(f"Combat {status['id']}, round {round_index + 1} : capture incomplète "
              f"({len(record['rounds'])} rounds sur {round_index}), pas de conseil.")
        return
    record = seen_by(record, side)
    if round_index == 0:
        print(f"\nCombat {status['id']} : {record['p0']['name']} contre {record['p1']['name']}")
    warn_if_engine_differs(record)
    print(advise(record, round_index + 1, enemy_card), flush=True)


def serve(me: str) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), StatusHandler)
    server.statuses = queue.Queue()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"En écoute sur http://127.0.0.1:{PORT} ; dans la console du client web : urConseil()", flush=True)
    advised = set()
    while True:
        try:
            on_status(latest(server.statuses), me, advised)
        except Exception as error:   # un état inattendu ne doit pas couper le conseil des rounds suivants
            print(f"Erreur sur cet état : {error!r}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--moi", required=True, help="votre pseudo Urban Rivals, tel qu'affiché en combat")
    parser.add_argument("--rejouer", metavar="COMBAT.json", help="conseiller un combat enregistré au lieu d'écouter")
    args = parser.parse_args()
    build_engine()
    if args.rejouer:
        replay_battle(args.rejouer, args.moi)
    else:
        serve(args.moi)


if __name__ == "__main__":
    main()
