"""
Le corpus combinatoire (src/core/engine/scenarios.py, corpus.py) est le test différentiel du moteur : chaque famille,
rejouée par le moteur de référence, doit redonner exactement le digest versionné dans data/engine_digests.json.
Un digest qui change signifie qu'une règle a changé : vérifier que c'est voulu, puis régénérer
(python scripts/build_engine_corpus.py) et commiter le nouveau digest avec la règle.
Les fichiers JSONL écrits doivent se relire tels quels (deck_from_dict, state_from_dict) : c'est ce que fera un port.
"""
import json
import os

import pytest

from src.core.engine.contract import Action, deck_from_dict, state_from_dict
from src.core.engine.corpus import VOCABULARY, family_summary, read_digests, vocabulary_digest, write_corpus
from src.core.engine.reference import play, terminal
from src.core.engine.scenarios import FAMILIES
from src.utils.config import BASE_DIR

pytestmark = pytest.mark.corpus

DIGESTS_PATH = os.path.join(BASE_DIR, "data", "engine_digests.json")
REGENERATE = "règle changée ? vérifier, puis : python scripts/build_engine_corpus.py"


@pytest.fixture(scope="module")
def pinned() -> dict:
    return read_digests(DIGESTS_PATH)


def test_every_family_is_pinned(pinned):
    assert set(pinned["families"]) == set(FAMILIES)


def test_vocabulary_digest_is_pinned(pinned):
    assert pinned["vocabulary"] == vocabulary_digest(), "vocabulaire du contrat changé : " + REGENERATE


@pytest.mark.parametrize("family", list(FAMILIES))
def test_family_replays_to_its_pinned_digest(pinned, family):
    assert family_summary(family) == pinned["families"][family], f"famille {family} : " + REGENERATE


def test_written_files_replay_from_json(tmp_path):
    digests = write_corpus(str(tmp_path), str(tmp_path / "digests.json"), families=["combat"])
    with open(tmp_path / "vocabulary.json", encoding="utf-8") as file:
        assert json.load(file) == json.loads(json.dumps(VOCABULARY))
    with open(tmp_path / "combat.decks.json", encoding="utf-8") as file:
        decks = [deck_from_dict(fields) for fields in json.load(file)]
    entries = 0
    with open(tmp_path / "combat.jsonl", encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)
            state = state_from_dict(entry["state"])
            assert terminal(state) is None
            next_state, outcome = play(decks[entry["deck"]], state, Action(*entry["ally_action"]), Action(*entry["enemy_action"]))
            assert next_state == state_from_dict(entry["next_state"]), entry["id"]
            assert {"ally": list(outcome.ally), "enemy": list(outcome.enemy)} == entry["outcome"], entry["id"]
            entries += 1
    assert entries == digests["families"]["combat"]["entries"] == len(open(tmp_path / "combat.jsonl", encoding="utf-8").readlines())
    assert len(decks) == digests["families"]["combat"]["decks"]
