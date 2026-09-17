#!/usr/bin/env python3
"""
Le solveur complet, hors ligne (docs/IA.md, étape 3 bis) : un affrontement de deux mains résolu de bout en bout,
exactement, dès le round 1 — l'ébauche « à temps illimité », et l'oracle contre lequel se mesurent les
approximations de l'étape 4.

    python scripts/solve_matchup.py --template                       # les mains de la partie d'exemple
    python scripts/solve_matchup.py --ally "Wardog:2,Meroo:1,Pino:2,Venus:3" --enemy "Lilith:3,Natrang:3,Sephora:2,Elixir:2"
    python scripts/solve_matchup.py --random --seed 3 --pillz 5      # deux mains tirées au hasard, partie réduite
    python scripts/solve_matchup.py --template --pillz 5 --epsilon   # + la meilleure réponse : ε doit valoir 0

Pour chaque premier joueur (tiré au sort en ELO) : valeur de la partie pour l'allié, carte et mises du round 1,
états visités par round, temps. La valeur du duel est la moyenne des deux. Avec --epsilon, ce qu'un adversaire
qui connaît la politique gagne au-delà de la valeur, de chaque côté — nul par construction, c'est la vérification.
Coût : quelques minutes à 5 pillz, de l'ordre de l'heure à 12 (mémoire : quelques centaines de Mo à quelques Go).
"""
import argparse
import json
import os
import random
import resource
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.ai import arena, engine, exploitability, solver          # noqa: E402
from src.core.domain.game import NB_ROUNDS, Game                       # noqa: E402
from src.utils.config import BASE_DIR                                  # noqa: E402


def parse_hand(text: str):
    """« Nom:étoiles,Nom:étoiles,… » → [(nom, étoiles), …]."""
    hand = []
    for item in text.split(","):
        name, _, stars = item.strip().rpartition(":")
        hand.append((name.strip(), int(stars)))
    return hand


def template_game(life: int, pillz: int, ally_first: bool) -> Game:
    """La partie d'exemple telle quelle (ses cartes ne sont pas toutes au catalogue officiel), remise au round 1."""
    with open(os.path.join(BASE_DIR, "data", "template_game_v1.json"), "r") as file:
        game = Game.from_dict_template(json.load(file))
    game.nb_turn, game.turn, game.history = 1, ally_first, []
    for player in (game.ally, game.enemy):
        player.life, player.pillz, player.effect_list = life, pillz, []
        for card in player.cards:
            card.played = False
    return game


def describe(solution: solver.Solution, state: Game) -> str:
    first = engine.player(state, solution.first)
    card = first.cards[solution.card]
    bets = ", ".join(f"{pick.pillz - 1}{'+fury' if pick.fury else ''} ({probability:.0%})"
                     for pick, probability in sorted(solution.bets.items(), key=lambda item: -item[1]))
    return f"{solution.first} pose {card.name} ({card.power}/{card.damage}) ; mises : {bets}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--template", action="store_true", help="les mains de la partie d'exemple")
    source.add_argument("--random", action="store_true", help="deux mains tirées au hasard (--seed)")
    source.add_argument("--ally", help="main alliée « Nom:étoiles,… » (avec --enemy)")
    parser.add_argument("--enemy", help="main ennemie « Nom:étoiles,… »")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--pillz", type=int, default=engine.STARTING_PILLZ, help="pillz de départ (défaut : 12)")
    parser.add_argument("--life", type=int, default=engine.ELO_LIFE, help="vies de départ (défaut : 14, ELO)")
    parser.add_argument("--epsilon", action="store_true", help="calculer aussi la meilleure réponse à la politique (long)")
    args = parser.parse_args()

    if args.template:
        make_state = lambda ally_first: template_game(args.life, args.pillz, ally_first)
    else:
        if args.random:
            rng = random.Random(args.seed)
            ally, enemy = arena.random_hand(rng), arena.random_hand(rng)
        elif args.enemy:
            ally, enemy = parse_hand(args.ally), parse_hand(args.enemy)
        else:
            parser.error("--ally demande --enemy")
        make_state = lambda ally_first: engine.new_game(ally, enemy, life=args.life, pillz=args.pillz, ally_first=ally_first)
    sample = make_state(True)
    for side in ("ally", "enemy"):
        cards = engine.player(sample, side).cards
        print(f"{side:<6} : {', '.join(f'{card.name} ({card.stars}★, {card.power}/{card.damage})' for card in cards)}")
    print(f"{args.life} vies, {args.pillz} pillz\n")

    solver.EXACT_ROUNDS = NB_ROUNDS
    values = []
    for ally_first in (True, False):
        state = make_state(ally_first)
        start = time.perf_counter()
        solution = solver.solve(state)
        elapsed = time.perf_counter() - start
        values.append(solution.value)
        per_round = {}
        for key in solver._values:
            per_round[key[0]] = per_round.get(key[0], 0) + 1
        states = ", ".join(f"round {round_number} : {count}" for round_number, count in sorted(per_round.items()))
        print(f"{'allié' if ally_first else 'ennemi'} premier : valeur {solution.value:+.4f} pour l'allié "
              f"({elapsed:.0f} s, {states}, {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} Mo)")
        print(f"    {describe(solution, state)}")
        if args.epsilon:
            for exploiter in ("enemy", "ally"):
                start = time.perf_counter()
                best = exploitability.best_response_value(state, exploiter, solver.distribution, memo={})
                gain = best - (solution.value if exploiter == "ally" else -solution.value)
                print(f"    ε ({exploiter} exploite) : {gain:+.6f}  ({time.perf_counter() - start:.0f} s)")
    print(f"\nvaleur du duel (premier joueur tiré au sort) : {sum(values) / 2:+.4f} pour l'allié")


if __name__ == "__main__":
    main()
