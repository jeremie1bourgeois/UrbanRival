import copy
import json
import os

import pytest

from src.core.domain.game import Game
from src.utils.config import BASE_DIR

TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "template_game_v1.json")


@pytest.fixture
def template_data() -> dict:
    with open(TEMPLATE_PATH, "r") as file:
        return json.load(file)


@pytest.fixture
def template_game(template_data) -> Game:
    return Game.from_dict_template(copy.deepcopy(template_data))
