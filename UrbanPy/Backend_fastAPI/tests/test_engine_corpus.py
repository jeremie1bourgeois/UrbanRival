"""
Le corpus (src/core/engine/corpus.py) doit être rejouable tel qu'il est écrit : chaque entrée relue depuis le JSON
et rejouée par le moteur de référence redonne l'état suivant enregistré — ce que devra faire un moteur compilé —,
et deux générations à graine égale sont identiques.
"""
import json

from src.core.engine.contract import Action, deck_from_dict, state_from_dict
from src.core.engine.corpus import VOCABULARY, build_corpus
from src.core.engine.reference import step, terminal


def _reloaded(corpus: dict) -> dict:
    return json.loads(json.dumps(corpus))


def test_every_entry_replays_from_json():
    corpus = _reloaded(build_corpus(games=20, extra_pairs=2, seed=0))
    assert corpus["vocabulary"] == _reloaded(VOCABULARY)
    plays = 0
    for game in corpus["games"]:
        deck = deck_from_dict(game["deck"])
        for entry in game["states"]:
            state = state_from_dict(entry["state"])
            assert terminal(state) is None
            for play in entry["plays"]:
                expected = state_from_dict(play["next_state"])
                assert step(deck, state, Action(*play["ally_action"]), Action(*play["enemy_action"])) == expected
                plays += 1
        assert terminal(state_from_dict(game["states"][-1]["plays"][0]["next_state"])) is not None
    assert plays == sum(len(entry["plays"]) for game in corpus["games"] for entry in game["states"])
    assert all(len(entry["plays"]) == 3 for game in corpus["games"] for entry in game["states"])


def test_same_seed_gives_the_same_corpus():
    assert build_corpus(games=5, extra_pairs=1, seed=7) == build_corpus(games=5, extra_pairs=1, seed=7)
    assert build_corpus(games=5, extra_pairs=1, seed=7) != build_corpus(games=5, extra_pairs=1, seed=8)
