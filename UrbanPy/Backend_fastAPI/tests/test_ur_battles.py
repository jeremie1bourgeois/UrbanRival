"""
Oracle : combats réels Urban Rivals capturés depuis le client officiel (data/ur_battles/*.json, voir
docs/ur-abilitydata-modele.md). Chaque round est rejoué dans le moteur avec les mêmes choix (carte, pillz, fury, ordre
de jeu) et les valeurs finales officielles sont exigées : puissance, dégâts, attaque, vainqueur, vies et pillz.
p0 est l'allié, p1 l'ennemi ; `first` dit qui joue en premier.
"""
import glob
import json
import os

import pytest

from src.adapters.repositories.card_repository import _official_cards
from src.core.domain.card import Card
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.use_cases.process_round import process_round
from src.schemas.game_schemas import ProcessRoundInput

BATTLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ur_battles")


def _battles():
    return sorted(glob.glob(os.path.join(BATTLES_DIR, "*.json")))


def _card(card_id: int, level: int) -> Card:
    name = next(name for name, data in _official_cards().items() if data["id"] == card_id)
    return Card(name, level)


def _game(record: dict) -> Game:
    players = [Player(name=record[side]["name"], life=record[side]["base_life"], pillz=record[side]["base_pillz"],
                      cards=[_card(c["id"], c["level"]) for c in record[side]["cards"]]) for side in ("p0", "p1")]
    return Game(1, True, players[0], players[1], [])


@pytest.mark.parametrize("path", _battles(), ids=os.path.basename)
def test_the_engine_reproduces_a_real_urban_rivals_battle(path):
    with open(path, encoding="utf-8") as file:
        record = json.load(file)
    game = _game(record)
    for round_ in record["rounds"]:
        game.turn = round_["first"] == "p0"
        p0, p1 = round_["p0"], round_["p1"]
        process_round(game, ProcessRoundInput(player1_card_index=p0["index"], player1_pillz=p0["pillz"], player1_fury=p0["fury"],
                                              player2_card_index=p1["index"], player2_pillz=p1["pillz"], player2_fury=p1["fury"]))
        ally, enemy = game.ally.cards[p0["index"]], game.enemy.cards[p1["index"]]
        observed = {
            "p0": {"power": ally.power_fight, "damage": ally.damage_fight, "attack": ally.attack, "won": ally.win},
            "p1": {"power": enemy.power_fight, "damage": enemy.damage_fight, "attack": enemy.attack, "won": enemy.win},
        }
        expected = {side: {k: round_[side][k] for k in ("power", "damage", "attack", "won")} for side in ("p0", "p1")}
        assert observed == expected, f"round {round_['round']} : {[e['text'] for e in game.history[-1].log]}"
        if round_["after"]["life"] is not None:
            assert [game.ally.life, game.enemy.life] == round_["after"]["life"], f"round {round_['round']} (vies)"
            assert [game.ally.pillz, game.enemy.pillz] == round_["after"]["pillz"], f"round {round_['round']} (pillz)"
