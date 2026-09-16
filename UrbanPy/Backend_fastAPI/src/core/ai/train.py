"""
L'entraînement, par « méthode des élites » (cross-entropy method).

Le principe tient en quatre lignes, et c'est ce qui le rend guidable :

1. On tire au sort une **population** de réglages (chaque réglage = un jeu de poids, donc une IA).
2. On fait jouer chacun un paquet de parties contre l'adversaire d'entraînement.
3. On garde les meilleurs — les **élites**.
4. On retire au sort autour des élites, et on recommence.

Pas de gradient, pas de réseau de neurones, pas de bibliothèque à installer. C'est moins puissant qu'un PPO,
mais ça tourne partout, ça converge vite sur 14 poids, et surtout on peut lire le résultat.

**Le détail qui fait tout** : à une génération donnée, tous les candidats jouent *exactement les mêmes parties*
(mêmes decks, même hasard). Sans cela on sélectionne le candidat le plus chanceux, pas le meilleur — et
l'entraînement n'avance pas. C'est l'erreur classique, et la raison d'être de `decks=` et `seed=` ci-dessous.
"""
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from src.core.ai.arena import DuelResult, Strategy, duel
from src.core.ai.engine_api import DeckPool
from src.core.ai.features import FEATURE_COUNT
from src.core.ai.opponent import STRATEGIES
from src.core.ai.policy import LinearPolicy, policy_strategy
from src.core.domain.card import Card

#: Plancher sur la dispersion : sans lui, la population se resserre trop vite et l'IA cesse d'explorer
#: (elle « se fige » sur la première stratégie à peu près correcte trouvée). Mesuré sur ce projet : à 0,05
#: l'exploration tombait à 0,10 dès la 16e génération et les scores cessaient de monter ; 0,15 laisse la
#: recherche respirer sans l'empêcher de se stabiliser.
MIN_SPREAD = 0.15


@dataclass
class TrainingConfig:
    """Les réglages de l'entraînement. Ce sont eux que tu ajustes pour guider l'IA."""
    generations: int = 20          # nombre de tours de la boucle ci-dessus
    population: int = 24           # candidats tirés au sort par génération
    elite_fraction: float = 0.25   # part des candidats conservés (0.25 = le quart supérieur)
    games_per_candidate: int = 40  # parties jouées par candidat pour le noter (pair : match aller-retour)
    opponent: str = "heuristic"    # "random", "heuristic", ou "self" (l'IA affronte sa propre version courante)
    initial_spread: float = 1.0    # dispersion du tirage initial des poids
    seed: int = 0
    only_supported_cards: bool = True   # n'entraîner que sur des cartes dont le moteur gère le pouvoir

    @property
    def elite_count(self) -> int:
        return max(2, round(self.population * self.elite_fraction))

    def describe(self) -> str:
        return (f"{self.generations} générations x {self.population} candidats x "
                f"{self.games_per_candidate} parties = "
                f"{self.generations * self.population * self.games_per_candidate} parties, "
                f"adversaire « {self.opponent} », graine {self.seed}")


@dataclass
class GenerationReport:
    """Ce qu'on sait à la fin d'une génération. Sert à suivre l'entraînement en direct."""
    generation: int
    best_score: float
    mean_score: float
    elite_mean_score: float
    spread: float              # dispersion moyenne des poids : élevée = explore encore, basse = s'est fixée
    seconds: float
    policy: LinearPolicy = field(repr=False)

    def line(self) -> str:
        return (f"génération {self.generation:>3} | meilleur {self.best_score * 100:5.1f} % | "
                f"moyenne {self.mean_score * 100:5.1f} % | élites {self.elite_mean_score * 100:5.1f} % | "
                f"exploration {self.spread:4.2f} | {self.seconds:5.1f}s")


def _opponent_strategy(config: TrainingConfig, current: LinearPolicy) -> Strategy:
    """L'adversaire d'entraînement. « self » = une copie figée de l'IA courante (auto-apprentissage)."""
    if config.opponent == "self":
        return policy_strategy(LinearPolicy(weights=list(current.weights)))
    if config.opponent not in STRATEGIES:
        raise ValueError(f"Adversaire inconnu : {config.opponent!r} "
                         f"(attendu : 'self' ou l'un de {sorted(STRATEGIES)})")
    return STRATEGIES[config.opponent]


def _score(candidate: LinearPolicy, opponent: Strategy, pool: DeckPool, config: TrainingConfig,
           decks: List[Tuple[List[Card], List[Card]]], seed: int) -> DuelResult:
    """Note d'un candidat : son taux de victoire sur le jeu de parties imposé à toute la génération."""
    return duel(policy_strategy(candidate), opponent, pool,
                games=config.games_per_candidate, rng=random.Random(seed),
                swap_sides=True, decks=decks)


def train(config: TrainingConfig, pool: Optional[DeckPool] = None,
          on_generation: Optional[Callable[[GenerationReport], None]] = None) -> Tuple[LinearPolicy, List[GenerationReport]]:
    """
    Lance l'entraînement et renvoie (la meilleure IA trouvée, le journal des générations).

    `on_generation` est appelé après chaque génération : c'est par là qu'on affiche la progression et qu'on
    enregistre les sauvegardes intermédiaires.
    """
    rng = random.Random(config.seed)
    if pool is None:
        from src.adapters.repositories.card_repository import official_card_catalogue
        pool = DeckPool(official_card_catalogue(), only_supported=config.only_supported_cards)

    # La population est décrite par un centre (les poids moyens) et une dispersion (de combien on s'en écarte).
    centre = [0.0] * FEATURE_COUNT
    spread = [config.initial_spread] * FEATURE_COUNT

    reports: List[GenerationReport] = []
    best_overall, best_overall_score = LinearPolicy(weights=list(centre)), -1.0

    for generation in range(1, config.generations + 1):
        started = time.perf_counter()

        # Le jeu de parties de cette génération : identique pour tous les candidats (cf. en-tête du module).
        deck_rng = random.Random(config.seed * 1000 + generation)
        decks = [pool.matchup(deck_rng) for _ in range(max(1, config.games_per_candidate // 2))]
        match_seed = config.seed * 1000 + generation

        opponent = _opponent_strategy(config, LinearPolicy(weights=list(centre)))

        candidates = [LinearPolicy(weights=[rng.gauss(mu, sigma) for mu, sigma in zip(centre, spread)])
                      for _ in range(config.population)]
        scored = [(candidate, _score(candidate, opponent, pool, config, decks, match_seed))
                  for candidate in candidates]
        scored.sort(key=lambda pair: pair[1].win_rate, reverse=True)

        elites = scored[: config.elite_count]
        # Nouveau centre = moyenne des élites ; nouvelle dispersion = leur écart-type (avec un plancher).
        centre = [statistics.fmean([elite.weights[i] for elite, _ in elites]) for i in range(FEATURE_COUNT)]
        spread = [max(MIN_SPREAD, statistics.pstdev([elite.weights[i] for elite, _ in elites]))
                  for i in range(FEATURE_COUNT)]

        best_candidate, best_result = scored[0]
        if best_result.win_rate > best_overall_score:
            best_overall_score = best_result.win_rate
            best_overall = LinearPolicy(weights=list(best_candidate.weights))

        report = GenerationReport(
            generation=generation,
            best_score=best_result.win_rate,
            mean_score=statistics.fmean([result.win_rate for _, result in scored]),
            elite_mean_score=statistics.fmean([result.win_rate for _, result in elites]),
            spread=statistics.fmean(spread),
            seconds=time.perf_counter() - started,
            policy=LinearPolicy(weights=list(centre)),
        )
        reports.append(report)
        if on_generation is not None:
            on_generation(report)

    # On renvoie le centre final : c'est la moyenne des élites, plus stable qu'un candidat isolé qui peut
    # devoir son score à un coup de chance résiduel.
    final = LinearPolicy(
        weights=list(centre),
        meta={
            "entrainement": config.describe(),
            "adversaire": config.opponent,
            "generations": config.generations,
            "population": config.population,
            "parties_par_candidat": config.games_per_candidate,
            "graine": config.seed,
            "meilleur_taux_vu": round(best_overall_score, 4),
            "taux_derniere_generation": round(reports[-1].best_score, 4) if reports else None,
        },
    )
    return final, reports
