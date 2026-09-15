"""
Rejoue chaque fixture de data/test/test_N (créée par le bouton "Sauvegarder le jeu pour les tests") :
l'état "prev" + le coup joué (lu dans "curr" : index dans history, pillz_fight et fury des cartes)
doit redonner exactement l'état "curr". Chaque partie validée à la main devient ainsi un test de régression.

Variable d'environnement URBANRIVAL_FIXTURES_DIR pour pointer sur un autre dossier de fixtures.
"""
import glob
import json
import os

import pytest

from src.core.domain.game import Game
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import ProcessRoundInput
from src.utils.config import BASE_DIR

FIXTURES_DIR = os.environ.get("URBANRIVAL_FIXTURES_DIR", os.path.join(BASE_DIR, "data", "test"))


def _fixture_dirs():
    dirs = glob.glob(os.path.join(FIXTURES_DIR, "test_*"))
    return sorted(dirs, key=lambda d: int(d.rsplit("_", 1)[1]))


def _load(fixture_dir: str, kind: str) -> dict:
    (path,) = glob.glob(os.path.join(fixture_dir, f"game_data_{kind}_*.json"))
    with open(path, "r") as file:
        return json.load(file)


def _play_saved_in(curr: dict) -> ProcessRoundInput:
    last_round = curr["history"][-1]
    ally_index, enemy_index = last_round["ally"]["card_index"], last_round["enemy"]["card_index"]
    ally_card, enemy_card = curr["ally"]["cards"][ally_index], curr["enemy"]["cards"][enemy_index]
    return ProcessRoundInput(
        player1_card_index=ally_index, player1_pillz=ally_card["pillz_fight"], player1_fury=ally_card["fury"],
        player2_card_index=enemy_index, player2_pillz=enemy_card["pillz_fight"], player2_fury=enemy_card["fury"],
    )


@pytest.mark.parametrize("fixture_dir", _fixture_dirs(), ids=os.path.basename)
def test_replaying_the_saved_play_reproduces_the_saved_state(fixture_dir):
    prev, curr = _load(fixture_dir, "prev"), _load(fixture_dir, "curr")
    game = Game.from_dict_template(prev)
    round_data = _play_saved_in(curr)

    check_round_correct(game, round_data)
    process_round(game, round_data)

    assert game.to_dict() == curr
