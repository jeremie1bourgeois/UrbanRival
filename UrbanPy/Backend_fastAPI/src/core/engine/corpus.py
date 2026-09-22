"""
Corpus de non-régression du moteur : des parties jouées au hasard par le moteur de référence, enregistrées sous la
forme du contrat (deck compilé, état, actions, état suivant). Tout moteur qui implémente le contrat — le port
compilé — doit reproduire chaque entrée exactement : c'est le test différentiel, à relancer à chaque changement de
règle. Chaque état enregistre le coup joué et quelques paires d'actions supplémentaires non jouées, pour couvrir plus
que la trajectoire. Le corpus se régénère à l'identique à graine égale : il n'est pas versionné.
"""
import random
from dataclasses import asdict

from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.engine.contract import (CLANS, CONDITIONS, EFFECT_KINDS, HOWS, TARGETS, TYPES, deck_from_game,
                                      state_from_game)
from src.core.engine.hands import random_hand
from src.core.engine.reference import legal_actions, step, terminal

VOCABULARY = {"hows": HOWS, "types": TYPES, "conditions": CONDITIONS, "targets": TARGETS, "clans": CLANS,
              "effect_kinds": EFFECT_KINDS}


def build_corpus(games: int, extra_pairs: int, seed: int) -> dict:
    rng = random.Random(seed)
    return {"seed": seed, "vocabulary": VOCABULARY, "games": [_random_game(rng, extra_pairs) for _ in range(games)]}


def _random_game(rng: random.Random, extra_pairs: int) -> dict:
    game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [])
    game.ally.cards, game.enemy.cards = random_hand(rng), random_hand(rng)
    deck, state = deck_from_game(game), state_from_game(game)
    states = []
    while terminal(state) is None:
        pairs = [(rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy")))
                 for _ in range(1 + extra_pairs)]
        next_states = [step(deck, state, ally_action, enemy_action) for ally_action, enemy_action in pairs]
        states.append({"state": asdict(state),
                       "plays": [{"ally_action": list(ally_action), "enemy_action": list(enemy_action),
                                  "next_state": asdict(next_state)}
                                 for (ally_action, enemy_action), next_state in zip(pairs, next_states)]})
        state = next_states[0]                              # la trajectoire suit le premier coup
    return {"deck": asdict(deck), "states": states}
