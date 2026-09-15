import glob
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

import src.core.services.game_service as game_service
from main import app
from tests.conftest import TEMPLATE_PATH


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Les parties sont lues sous BASE_DIR et écrites dans le dossier courant : on aligne les deux sur tmp_path.
    os.makedirs(tmp_path / "data")
    shutil.copy(TEMPLATE_PATH, tmp_path / "data" / "template_game_v1.json")
    monkeypatch.setattr(game_service, "BASE_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return TestClient(app)


def _play(client, game_id, ally_index, enemy_index):
    return client.post(
        f"/process_round/{game_id}",
        json={"player1_card_index": ally_index, "player1_pillz": 1, "player1_fury": False,
              "player2_card_index": enemy_index, "player2_pillz": 1, "player2_fury": False},
    )


def test_full_game_lasts_four_rounds_then_refuses_a_fifth(client):
    game_id = client.get("/init_game/template").json()["game_id"]

    responses = [_play(client, game_id, i, i) for i in range(4)]

    assert [r.status_code for r in responses] == [200] * 4
    assert [r.json()["game"]["nb_turn"] for r in responses] == [2, 3, 4, 5]
    assert responses[-1].json()["state"] != "Game Not Finished"
    assert _play(client, game_id, 0, 0).status_code == 400


def test_save_for_test_stores_two_consecutive_states(client, tmp_path):
    game_id = client.get("/init_game/template").json()["game_id"]
    _play(client, game_id, 0, 0)
    _play(client, game_id, 1, 1)

    assert client.get("/save_for_test", params={"game_id": game_id}).status_code == 200

    (prev_path,) = glob.glob(str(tmp_path / "data" / "test" / "test_1" / "game_data_prev_*.json"))
    (curr_path,) = glob.glob(str(tmp_path / "data" / "test" / "test_1" / "game_data_curr_*.json"))
    prev, curr = json.load(open(prev_path)), json.load(open(curr_path))
    assert (prev["nb_turn"], curr["nb_turn"]) == (2, 3)
    assert len(prev["history"]) == 1 and len(curr["history"]) == 2


REAL_DECK = {
    "player1": [{"card_name": "Aamir", "nb_stars": 3}, {"card_name": "Allison", "nb_stars": 3},
                {"card_name": "Amelia", "nb_stars": 3}, {"card_name": "Ashley", "nb_stars": 2}],
    "player2": [{"card_name": "Asporov", "nb_stars": 4}, {"card_name": "B Mappe Mt", "nb_stars": 5},
                {"card_name": "Bhudd", "nb_stars": 3}, {"card_name": "Serafina", "nb_stars": 5}],
}


def test_init_game_with_real_cards_then_play_a_round(client):
    response = client.post("/init_game/", json=REAL_DECK)

    assert response.status_code == 200, response.json()
    body = response.json()
    game_id = body["game_id"]
    assert body["game"]["nb_turn"] == 1
    aamir = body["game"]["ally"]["cards"][0]
    assert (aamir["power"], aamir["damage"], aamir["ability"]["how"]) == (5, 4, "growth")

    played = _play(client, game_id, 0, 2)   # Aamir vs Bhudd

    assert played.status_code == 200, played.json()
    assert played.json()["game"]["nb_turn"] == 2


def test_init_game_with_unknown_card_is_a_client_error(client):
    deck = {**REAL_DECK, "player1": [{"card_name": "Zorglub", "nb_stars": 1}] + REAL_DECK["player1"][1:]}

    response = client.post("/init_game/", json=deck)

    assert (response.status_code, response.json()["detail"]) == (400, "No card found with name: Zorglub")
