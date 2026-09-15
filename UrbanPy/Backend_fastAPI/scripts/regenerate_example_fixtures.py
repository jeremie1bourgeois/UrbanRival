"""
Régénère les fixtures d'exemple data/test/test_1..3 par le mécanisme réel (API + /save_for_test) dans un
bac à sable, puis les copie dans data/test. À relancer quand le format de partie ou le template change.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/regenerate_example_fixtures.py
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import src.core.services.game_service as game_service  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

# (index allié, index ennemi, pillz allié, pillz ennemi, fury allié, fury ennemi) — résultats vérifiés à la main
PLAYS = [
    (2, 2, 3, 3, False, False),  # Amelia vs Bhudd (stop bonus)         -> ennemi 12 -> 7
    (1, 0, 2, 2, False, False),  # Allison vs Asporov (support)         -> allié 12 -> 6
    (0, 1, 2, 2, True, False),   # Agustino fury vs B Mappe (equalizer) -> ennemi 7 -> 4, pillz 9 -> 5
]


def main() -> None:
    sandbox = tempfile.mkdtemp(prefix="urban_fixtures_")
    os.makedirs(os.path.join(sandbox, "data"))
    shutil.copy(os.path.join(BASE_DIR, "data", "template_game_v1.json"), os.path.join(sandbox, "data"))
    game_service.BASE_DIR = sandbox
    os.chdir(sandbox)

    from fastapi.testclient import TestClient  # noqa: E402
    from main import app  # noqa: E402

    client = TestClient(app)
    game_id = client.get("/init_game/template").json()["game_id"]
    for ally, enemy, ally_pillz, enemy_pillz, ally_fury, enemy_fury in PLAYS:
        played = client.post(f"/process_round/{game_id}", json={
            "player1_card_index": ally, "player1_pillz": ally_pillz, "player1_fury": ally_fury,
            "player2_card_index": enemy, "player2_pillz": enemy_pillz, "player2_fury": enemy_fury,
        })
        assert played.status_code == 200, played.json()
        saved = client.get("/save_for_test", params={"game_id": game_id})
        assert saved.status_code == 200, saved.json()

    target = os.path.join(BASE_DIR, "data", "test")
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(os.path.join(sandbox, "data", "test"), target)
    print(f"{len(PLAYS)} fixtures régénérées dans {target}")


if __name__ == "__main__":
    main()
