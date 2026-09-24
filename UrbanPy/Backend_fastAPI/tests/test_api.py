import glob
import json
import logging
import os
import shutil

import pytest
from fastapi.testclient import TestClient

import src.core.services.game_service as game_service
from main import app
from src.utils.config import FRONT_DEV_ORIGIN, cors_origins
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


def test_process_round_rejects_bets_and_card_indices_outside_the_rules(client):
    """Une mise vaut au moins la pillz gratuite et une carte est en main : sinon le joueur gagnerait des pillz
    (mise négative) ou jouerait une carte par un index négatif, que Python lit à l'envers."""
    game_id = client.get("/init_game/template").json()["game_id"]
    base = {"player1_card_index": 0, "player1_pillz": 1, "player1_fury": False,
            "player2_card_index": 0, "player2_pillz": 1, "player2_fury": False}

    for invalide in ({"player1_pillz": 0}, {"player1_pillz": -5}, {"player2_pillz": -1},
                     {"player1_card_index": -1}, {"player2_card_index": 4}):
        response = client.post(f"/process_round/{game_id}", json={**base, **invalide})
        assert response.status_code in (400, 422), f"{invalide} accepté : {response.json()}"

    assert client.post(f"/process_round/{game_id}", json=base).status_code == 200


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


def test_init_game_reports_the_night_draw_and_accepts_a_forced_value(client):
    drawn = client.post("/init_game/", json=REAL_DECK).json()["game"]["night"]
    forced = client.post("/init_game/", json={**REAL_DECK, "night": True}).json()["game"]

    assert drawn in (True, False)
    assert forced["night"] is True


def test_init_game_takes_the_starting_situation_of_any_game_mode(client):
    """Vies et pillz de chaque joueur (en Survivor ils diffèrent), premier joueur imposé ; défauts : 12, 12, joueur 1."""
    response = client.post("/init_game/", json={**REAL_DECK, "life": [16, 12], "pillz": [8, 12], "first": "player2"})

    assert response.status_code == 200, response.json()
    game = response.json()["game"]
    assert (game["ally"]["life"], game["enemy"]["life"]) == (16, 12)
    assert (game["ally"]["pillz"], game["enemy"]["pillz"]) == (8, 12)
    assert game["turn"] is False                      # le joueur 2 pose en premier

    same_for_both = client.post("/init_game/", json={**REAL_DECK, "life": 15}).json()["game"]
    assert (same_for_both["ally"]["life"], same_for_both["enemy"]["life"]) == (15, 15)
    assert (same_for_both["ally"]["pillz"], same_for_both["enemy"]["pillz"]) == (12, 12)
    assert same_for_both["turn"] is True


def test_init_game_defaults_to_the_classic_situation(client):
    game = client.post("/init_game/", json=REAL_DECK).json()["game"]

    assert (game["ally"]["life"], game["ally"]["pillz"], game["turn"]) == (12, 12, True)


def test_init_game_can_draw_the_first_player(client):
    drawn = {client.post("/init_game/", json={**REAL_DECK, "first": "random"}).json()["game"]["turn"] for _ in range(12)}

    assert drawn == {True, False}


def test_init_game_rejects_an_invalid_starting_situation(client):
    assert client.post("/init_game/", json={**REAL_DECK, "first": "player3"}).status_code == 422
    assert client.post("/init_game/", json={**REAL_DECK, "life": 0}).status_code == 422
    assert client.post("/init_game/", json={**REAL_DECK, "pillz": -1}).status_code == 422
    assert client.post("/init_game/", json={**REAL_DECK, "pillz": [12, 12, 12]}).status_code == 422


def test_init_game_rejects_an_invalid_hand(client):
    """Une main compte exactement 4 cartes et un niveau va de 1 à 5 (contraintes de `PlayerCards`/`CardInput`)."""
    assert client.post("/init_game/", json={**REAL_DECK, "player1": REAL_DECK["player1"][:3]}).status_code == 422
    assert client.post("/init_game/", json={**REAL_DECK,
                                            "player2": REAL_DECK["player2"] + [{"card_name": "Aamir"}]}).status_code == 422

    niveau_hors_bornes = [{"card_name": "Aamir", "nb_stars": 7}] + REAL_DECK["player1"][1:]
    assert client.post("/init_game/", json={**REAL_DECK, "player1": niveau_hors_bornes}).status_code == 422


def test_init_game_with_unknown_card_is_a_client_error(client):
    deck = {**REAL_DECK, "player1": [{"card_name": "Zorglub", "nb_stars": 1}] + REAL_DECK["player1"][1:]}

    response = client.post("/init_game/", json=deck)

    assert (response.status_code, response.json()["detail"]) == (400, "No card found with name: Zorglub")


def test_une_erreur_inattendue_devient_un_500_sobre(client, caplog):
    """Une exception qui échappe aux routes est journalisée côté serveur et rendue en 500 : le client
    ne voit ni la trace ni le message d'origine."""
    @app.get("/panne_de_test")
    def panne():
        raise RuntimeError("rouage cassé")

    try:
        with caplog.at_level(logging.ERROR):
            reponse = client.get("/panne_de_test")
    finally:
        app.router.routes.pop()

    assert reponse.status_code == 500
    assert reponse.json() == {"detail": "Erreur interne. Consultez les logs pour plus d'informations."}
    assert "rouage cassé" not in reponse.text
    assert "rouage cassé" in caplog.text, "la trace doit rester dans les logs du serveur"


def test_cors_origins_come_from_the_environment(monkeypatch):
    """Le front local est le défaut ; un déploiement déclare ses origines dans UR_CORS_ORIGINS."""
    monkeypatch.delenv("UR_CORS_ORIGINS", raising=False)
    assert cors_origins() == [FRONT_DEV_ORIGIN]

    monkeypatch.setenv("UR_CORS_ORIGINS", "https://urbanrival.example, http://127.0.0.1:4173")
    assert cors_origins() == ["https://urbanrival.example", "http://127.0.0.1:4173"]


def test_api_answers_cors_to_the_configured_front_only(client):
    autorisee = client.get("/cards", headers={"Origin": FRONT_DEV_ORIGIN})
    etrangere = client.get("/cards", headers={"Origin": "https://ailleurs.example"})

    assert autorisee.headers.get("access-control-allow-origin") == FRONT_DEV_ORIGIN
    assert "access-control-allow-origin" not in etrangere.headers


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
