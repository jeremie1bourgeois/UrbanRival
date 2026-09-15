"""
Balayage de robustesse du moteur : chaque description officielle supportée par le parseur est posée comme
ability d'une carte du template, puis un round est joué en victoire / défaite, en jouant premier / second,
avec et sans round précédent. Liste les descriptions qui lèvent une exception, groupées par erreur.
« Ne plante pas » ne veut pas dire « correct » : c'est un filet, pas une validation des règles.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/engine_crash_sweep.py
"""
import contextlib
import copy
import io
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.repositories.card_repository import all_capacity_descriptions  # noqa: E402
from src.core.domain.game import Game  # noqa: E402
from src.core.domain.round import Round  # noqa: E402
from src.core.parsing.capacity_parser import parse_capacity  # noqa: E402
from src.core.use_cases.process_round import check_round_correct, process_round  # noqa: E402
from src.schemas.game_schemas import ProcessRoundInput  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

AMELIA, ASPOROV = 2, 0   # allié P3 D5 (ability remplacée) contre ennemi P7 D3


def play(template: dict, capacity, ally_wins: bool, ally_plays_first: bool, with_history: bool) -> None:
    game = Game.from_dict_template(copy.deepcopy(template))
    game.turn = ally_plays_first
    if with_history:
        previous = Round()
        previous.ally.win, previous.enemy.win = (not ally_wins), ally_wins
        game.history.append(previous)
    game.ally.cards[AMELIA].ability = copy.deepcopy(capacity)
    round_data = ProcessRoundInput(player1_card_index=AMELIA, player1_pillz=6 if ally_wins else 1,
                                   player2_card_index=ASPOROV, player2_pillz=1 if ally_wins else 6)
    check_round_correct(game, round_data)
    with contextlib.redirect_stdout(io.StringIO()):
        process_round(game, round_data)


def main() -> None:
    with open(os.path.join(BASE_DIR, "data", "template_game_v1.json"), "r") as file:
        template = json.load(file)
    errors = defaultdict(list)
    playable = 0
    for text in sorted(all_capacity_descriptions()):
        parsed = parse_capacity(text)
        if not parsed.supported or parsed.capacity is None:
            continue
        failure = None
        for ally_wins in (True, False):
            for ally_plays_first in (True, False):
                for with_history in (False, True):
                    try:
                        play(template, parsed.capacity, ally_wins, ally_plays_first, with_history)
                    except Exception as error:  # noqa: BLE001 - on veut tout attraper
                        failure = f"{type(error).__name__}: {str(error)[:100]}"
                if failure:
                    break
            if failure:
                break
        if failure:
            errors[failure].append(text)
        else:
            playable += 1

    print(f"{playable} descriptions jouent sans exception, {sum(len(v) for v in errors.values())} plantent")
    for failure, texts in sorted(errors.items(), key=lambda item: -len(item[1])):
        print(f"\n[{len(texts)}] {failure}")
        for text in texts:
            print(f"    {text}")


if __name__ == "__main__":
    main()
