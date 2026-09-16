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


def test_save_for_test_can_freeze_an_earlier_round_once_the_game_moved_on(client, tmp_path):
    """Le cas qui bloquait : on repère au round 4 que le round 2 était douteux, et on le fige après coup."""
    game_id = client.get("/init_game/template").json()["game_id"]
    for i in range(4):
        _play(client, game_id, i, i)

    assert client.get("/save_for_test", params={"game_id": game_id, "nb_turn": 3}).status_code == 200

    (prev_path,) = glob.glob(str(tmp_path / "data" / "test" / "test_1" / "game_data_prev_*.json"))
    (curr_path,) = glob.glob(str(tmp_path / "data" / "test" / "test_1" / "game_data_curr_*.json"))
    prev, curr = json.load(open(prev_path)), json.load(open(curr_path))
    assert (prev["nb_turn"], curr["nb_turn"]) == (2, 3)


def test_save_for_test_rejects_a_round_the_game_never_reached(client):
    game_id = client.get("/init_game/template").json()["game_id"]
    _play(client, game_id, 0, 0)

    response = client.get("/save_for_test", params={"game_id": game_id, "nb_turn": 4})

    assert response.status_code == 400
    assert "not played" in response.json()["detail"]


REAL_DECK = {
    "player1": [{"card_name": "Aamir", "nb_stars": 3}, {"card_name": "Allison", "nb_stars": 3},
                {"card_name": "Amelia", "nb_stars": 3}, {"card_name": "Ashley", "nb_stars": 2}],
    "player2": [{"card_name": "Asporov", "nb_stars": 4}, {"card_name": "B Mappe Cr", "nb_stars": 5},
                {"card_name": "Bhudd", "nb_stars": 3}, {"card_name": "Serafina Cr", "nb_stars": 5}],
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


def test_cards_catalogue_lists_every_official_card_with_its_levels(client):
    response = client.get("/cards")

    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 2497   # instantané iclintz du 2026-09-15
    aamir = next(card for card in cards if card["name"] == "Aamir")
    assert (aamir["faction"], aamir["starOff"], aamir["bonus"], aamir["bonus_supported"]) == ("All Stars", 3, "-2 Opp Power, Min 1", True)
    assert [(level["stars"], level["power"], level["damage"], level["ability"], level["ability_supported"]) for level in aamir["levels"]] == [
        (1, 3, 4, "Ability at Level 3", True),
        (2, 4, 4, "Ability at Level 3", True),
        (3, 5, 4, "Growth: -1 Opp Power, Min 4", True),
    ]
    genesis = next(card for card in cards if card["name"] == "Genesis")
    assert next(level for level in genesis["levels"] if level["stars"] == 5)["ability_supported"] is False


def test_cards_catalogue_exposes_images(client, monkeypatch):
    import src.adapters.repositories.card_repository as card_repository
    from tests.test_card_loading import OFFICIAL_WITH_IMAGES
    monkeypatch.setattr(card_repository, "_official_cards", lambda: OFFICIAL_WITH_IMAGES)
    card_repository.official_card_catalogue.cache_clear()

    (aamir,) = client.get("/cards").json()

    assert aamir["clan_image"] == "https://cdn.example/clan/ALLSTARS.png"
    assert aamir["levels"][0]["image"] == "https://cdn.example/aamir_3.png"
    card_repository.official_card_catalogue.cache_clear()


def test_ai_pick_endpoint_returns_a_legal_pick(client):
    game_id = client.get("/init_game/template").json()["game_id"]

    response = client.post(f"/ai_pick/{game_id}", json={"strategy": "heuristic", "side": "enemy"})

    assert response.status_code == 200, response.json()
    pick = response.json()
    assert pick["card_index"] in range(4) and pick["pillz"] >= 1 and isinstance(pick["fury"], bool)
    played = client.post(f"/process_round/{game_id}", json={"player1_card_index": 0, "player1_pillz": 1, "player1_fury": False,
                                                            "player2_card_index": pick["card_index"], "player2_pillz": pick["pillz"], "player2_fury": pick["fury"]})
    assert played.status_code == 200, played.json()


def test_ai_pick_rejects_an_unknown_strategy(client):
    game_id = client.get("/init_game/template").json()["game_id"]

    response = client.post(f"/ai_pick/{game_id}", json={"strategy": "psychic", "side": "enemy"})

    assert response.status_code == 400


@pytest.fixture
def trained_policy_installed():
    """Installe / retire l'IA entraînée en mémoire, pour ne pas dépendre de la présence de data/ai/policy.json
    sur la machine qui lance les tests."""
    from src.core.ai import trained
    from src.core.ai.policy import LinearPolicy

    def install(available: bool):
        trained.forget_cached_policy()
        trained._cache[trained.DEFAULT_POLICY_PATH] = LinearPolicy() if available else None

    yield install
    from src.core.ai import trained as module
    module.forget_cached_policy()


def test_ai_strategies_lists_the_three_opponents(client):
    response = client.get("/ai_strategies")

    assert response.status_code == 200
    strategies = {entry["name"]: entry for entry in response.json()}
    assert set(strategies) == {"random", "heuristic", "trained"}
    assert strategies["heuristic"]["available"] is True


def test_the_trained_opponent_is_announced_unavailable_until_one_is_trained(client, trained_policy_installed):
    """Mieux vaut ne pas le proposer que le proposer et échouer au premier coup."""
    trained_policy_installed(False)

    strategies = {entry["name"]: entry for entry in client.get("/ai_strategies").json()}

    assert strategies["trained"]["available"] is False


def test_the_trained_opponent_becomes_available_once_a_policy_exists(client, trained_policy_installed):
    trained_policy_installed(True)

    strategies = {entry["name"]: entry for entry in client.get("/ai_strategies").json()}

    assert strategies["trained"]["available"] is True
