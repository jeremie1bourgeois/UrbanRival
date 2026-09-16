"""
L'arène : faire s'affronter deux IA et mesurer laquelle est la meilleure.

Le piège à éviter : **la chance au tirage**. Si l'IA A tire Kolos et l'IA B tire une commune à 2 étoiles, A gagne
sans rien prouver. Sur quelques centaines de parties, ce bruit peut suffire à croire qu'un entraînement a marché
alors qu'il n'a rien fait.

Deux garde-fous ici :

1. **Le match retour** (`swap_sides`) : chaque paire de decks est jouée deux fois, les camps inversés. Si A gagne
   les deux, c'est A ; si chacun gagne avec le bon deck, c'est le deck. C'est le garde-fou le plus important.
2. **La marge d'erreur** : le taux de victoire est rendu avec son incertitude. 52 % ± 4 %, ce n'est pas mieux
   que 50 % — c'est indistinguable, et il faut plus de parties avant de conclure quoi que ce soit.
"""
import math
import random
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from src.core.ai.engine_api import DeckPool, is_terminal, new_game, step, winner
from src.core.ai.opponent import Pick
from src.core.domain.card import Card
from src.core.domain.game import Game

#: Une stratégie prend la partie et son camp, et renvoie un coup. Même signature que `opponent.STRATEGIES`.
Strategy = Callable[[Game, str, random.Random], Pick]


@dataclass(frozen=True)
class GameOutcome:
    winner: str            # "ally", "enemy" ou "draw"
    life_gap: int          # vie allié - vie ennemi à la fin
    rounds: int


def play_game(ally_strategy: Strategy, enemy_strategy: Strategy,
              ally_cards: List[Card], enemy_cards: List[Card],
              rng: random.Random) -> GameOutcome:
    """Une partie complète, du premier round à la fin."""
    state = new_game(ally_cards, enemy_cards)
    rounds = 0
    while not is_terminal(state):
        ally_action = ally_strategy(state, "ally", rng)
        enemy_action = enemy_strategy(state, "enemy", rng)
        state, result = step(state, ally_action, enemy_action)
        rounds += 1
    return GameOutcome(winner=winner(state), life_gap=state.ally.life - state.enemy.life, rounds=rounds)


@dataclass(frozen=True)
class DuelResult:
    """Le bilan d'un affrontement, du point de vue de la première IA."""
    games: int
    wins: int
    losses: int
    draws: int
    mean_life_gap: float

    @property
    def win_rate(self) -> float:
        """Les nuls comptent pour une demi-victoire (usage courant aux échecs)."""
        return (self.wins + 0.5 * self.draws) / self.games if self.games else 0.0

    @property
    def margin(self) -> float:
        """Marge d'erreur à ~95 % sur le taux de victoire. Deux écarts-types, formule binomiale."""
        if self.games == 0:
            return 0.0
        rate = self.win_rate
        return 1.96 * math.sqrt(max(rate * (1.0 - rate), 1e-9) / self.games)

    @property
    def conclusive(self) -> bool:
        """Vrai si l'écart avec 50 % dépasse la marge d'erreur : on peut conclure."""
        return abs(self.win_rate - 0.5) > self.margin

    def summary(self, name_a: str = "A", name_b: str = "B") -> str:
        verdict = "significatif" if self.conclusive else "NON significatif (il faut plus de parties)"
        return (f"{name_a} contre {name_b} : {self.win_rate * 100:.1f} % ± {self.margin * 100:.1f} % "
                f"({self.wins} V / {self.losses} D / {self.draws} N sur {self.games} parties, "
                f"écart de vie moyen {self.mean_life_gap:+.2f}) — {verdict}")


def duel(strategy_a: Strategy, strategy_b: Strategy, pool: DeckPool, games: int,
         rng: random.Random, swap_sides: bool = True,
         decks: Optional[List[Tuple[List[Card], List[Card]]]] = None) -> DuelResult:
    """
    Fait jouer A contre B sur `games` parties et renvoie le bilan **du point de vue de A**.

    Avec `swap_sides` (par défaut), les parties vont par paires : la même paire de decks est jouée une fois avec
    A côté allié, une fois avec A côté ennemi. `games` est arrondi au nombre pair inférieur.
    """
    wins = losses = draws = 0
    life_gaps: List[int] = []
    matchups = games // 2 if swap_sides else games

    for index in range(matchups):
        if decks is not None:
            deck_a, deck_b = decks[index % len(decks)]
        else:
            deck_a, deck_b = pool.matchup(rng)

        # Manche aller : A est l'allié.
        outcome = play_game(strategy_a, strategy_b, deck_a, deck_b, rng)
        wins += outcome.winner == "ally"
        losses += outcome.winner == "enemy"
        draws += outcome.winner == "draw"
        life_gaps.append(outcome.life_gap)

        if not swap_sides:
            continue

        # Manche retour : mêmes decks, A passe côté ennemi. Le résultat se lit à l'envers.
        outcome = play_game(strategy_b, strategy_a, deck_a, deck_b, rng)
        wins += outcome.winner == "enemy"
        losses += outcome.winner == "ally"
        draws += outcome.winner == "draw"
        life_gaps.append(-outcome.life_gap)

    played = wins + losses + draws
    return DuelResult(games=played, wins=wins, losses=losses, draws=draws,
                      mean_life_gap=sum(life_gaps) / len(life_gaps) if life_gaps else 0.0)
