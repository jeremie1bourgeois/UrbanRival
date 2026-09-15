import copy
import glob
import json
import os

import pytest

import src.core.services.game_service as game_service
from src.core.services.game_service import save_for_test_service


def _write_game_file(directory: str, game_id: int, nb_turn: int, template_data: dict, ally_life: int):
    data = copy.deepcopy(template_data)
    data["nb_turn"] = nb_turn
    data["ally"]["life"] = ally_life
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, f"game_data_{game_id}_{nb_turn}.json"), "w") as file:
        json.dump(data, file)


def _load_saved(test_directory: str, kind: str) -> dict:
    (path,) = glob.glob(os.path.join(test_directory, f"game_data_{kind}_*.json"))
    with open(path, "r") as file:
        return json.load(file)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    # Le service écrit sous BASE_DIR et, pour l'id de test, dans le dossier courant.
    monkeypatch.setattr(game_service, "BASE_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_save_for_test_keeps_previous_and_current_round_states(sandbox, template_data):
    game_dir = os.path.join(sandbox, "data", "game", "game_7")
    _write_game_file(game_dir, 7, nb_turn=1, template_data=template_data, ally_life=12)
    _write_game_file(game_dir, 7, nb_turn=2, template_data=template_data, ally_life=9)

    save_for_test_service(7)

    test_dir = os.path.join(sandbox, "data", "test", "test_1")
    prev, curr = _load_saved(test_dir, "prev"), _load_saved(test_dir, "curr")
    assert (prev["nb_turn"], prev["ally"]["life"]) == (1, 12)
    assert (curr["nb_turn"], curr["ally"]["life"]) == (2, 9)


def test_save_for_test_id_does_not_depend_on_current_directory(sandbox, template_data, monkeypatch):
    game_dir = os.path.join(sandbox, "data", "game", "game_7")
    _write_game_file(game_dir, 7, nb_turn=1, template_data=template_data, ally_life=12)
    _write_game_file(game_dir, 7, nb_turn=2, template_data=template_data, ally_life=9)
    for existing in ("test_1", "test_2"):
        os.makedirs(os.path.join(sandbox, "data", "test", existing))
    elsewhere = sandbox / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    save_for_test_service(7)

    assert os.path.isdir(os.path.join(sandbox, "data", "test", "test_3"))
