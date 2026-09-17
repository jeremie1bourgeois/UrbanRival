#!/usr/bin/env python3
"""
Balayage de la matrice de round rapide (docs/IA.md, étape 3) : chaque description officielle gérée par le parseur
est posée comme ability d'une carte de la partie d'exemple, puis toutes les mises d'un round 3 (deux cartes par
camp, 3 pillz chacun, vies basses) sont comparées, cellule à cellule, entre `round_matrix.values` et
`engine.step` — sur la clé canonique de l'état suivant, allié premier puis second, sans et avec round précédent.
Liste les descriptions qui diffèrent (elles interdisent le raccourci : à ajouter à la liste des capacités
sensibles) et compte celles qui passent par le repli.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/round_matrix_sweep.py
"""
import contextlib
import copy
import io
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.repositories.card_repository import all_capacity_descriptions   # noqa: E402
from src.core.ai import engine, round_matrix, solver                              # noqa: E402
from src.core.domain.game import NB_ROUNDS, Game                                  # noqa: E402
from src.core.domain.round import Round                                           # noqa: E402
from src.core.parsing.capacity_parser import parse_capacity                       # noqa: E402
from src.utils.config import BASE_DIR                                             # noqa: E402

AMELIA = 2      # allié P3 D5, dont l'ability est remplacée
PILLZ = 3
LIFE = (4, 5)


def third_round(template: dict, capacity, ally_first: bool, with_history: bool) -> Game:
    game = Game.from_dict_template(copy.deepcopy(template))
    game.ally.cards[AMELIA].ability = copy.deepcopy(capacity)
    game.nb_turn = NB_ROUNDS - 1
    game.turn = ally_first
    game.ally.life, game.enemy.life = LIFE
    game.ally.pillz = game.enemy.pillz = PILLZ
    for cards in (game.ally.cards, game.enemy.cards):
        cards[0].played = cards[1].played = True
    if with_history:
        previous = Round()
        previous.ally.card_index, previous.enemy.card_index = 1, 1
        previous.ally.win, previous.enemy.win = False, True
        game.history.append(previous)
    return game


def engine_values(state, first, card_first, card_second):
    second = engine.other(first)
    return {(own, theirs): solver.canonical_key(engine.next_state(state, first, own, theirs))
            for own in engine.legal_actions(state, first) if own.card_index == card_first
            for theirs in engine.legal_actions(state, second) if theirs.card_index == card_second}


def compare(state, first) -> bool:
    for card_first in (2, 3):
        for card_second in (2, 3):
            fast = round_matrix.values(state, first, card_first, card_second, solver.canonical_key)
            if fast != engine_values(state, first, card_first, card_second):
                return False
    return True


def main() -> None:
    with open(os.path.join(BASE_DIR, "data", "template_game_v1.json"), "r") as file:
        template = json.load(file)
    mismatches, errors = [], defaultdict(list)
    identical = sensitive = 0
    for text in sorted(all_capacity_descriptions()):
        parsed = parse_capacity(text)
        if not parsed.supported or parsed.capacity is None:
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                states = [third_round(template, parsed.capacity, ally_first, with_history)
                          for ally_first in (True, False) for with_history in (False, True)]
                if round_matrix.bet_sensitive(states[0]):
                    sensitive += 1
                if all(compare(state, engine.first_side(state)) for state in states):
                    identical += 1
                else:
                    mismatches.append(text)
        except Exception as error:  # noqa: BLE001
            errors[f"{type(error).__name__}: {str(error)[:100]}"].append(text)

    print(f"{identical} descriptions identiques au moteur cellule à cellule (dont {sensitive} par le repli), "
          f"{len(mismatches)} diffèrent, {sum(len(v) for v in errors.values())} plantent")
    for text in mismatches:
        print(f"    DIFFÈRE  {text}")
    for failure, texts in sorted(errors.items(), key=lambda item: -len(item[1])):
        print(f"\n[{len(texts)}] {failure}")
        for text in texts:
            print(f"    {text}")


if __name__ == "__main__":
    main()
