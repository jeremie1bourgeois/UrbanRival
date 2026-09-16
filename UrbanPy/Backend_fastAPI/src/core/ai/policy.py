"""
L'IA proprement dite : une « politique », c'est-à-dire la règle qui transforme une situation en un coup.

Ici la règle est une simple note pondérée (voir `features.py`) :

    note(coup) = poids_1 x critère_1 + poids_2 x critère_2 + ...

et l'IA **tire au sort** parmi les coups en favorisant les mieux notés. Tout ce que l'entraînement modifie,
ce sont les poids.

Pourquoi tirer au sort plutôt que jouer bêtement le mieux noté ? Deux raisons, et la deuxième a décidé de la
conception :

1. Les deux joueurs choisissent **en même temps**, sans voir le coup d'en face. Une IA parfaitement prévisible se
   fait donc exploiter : il suffit de savoir ce qu'elle va jouer pour la battre. Jouer « souvent le bon coup, pas
   toujours le même » est la bonne réponse, et c'est un résultat classique de théorie des jeux.
2. Cela rend l'entraînement possible. Mesuré sur ce projet : une formule au hasard qui joue toujours son coup
   préféré gagne **1,2 %** de ses parties contre l'heuristique — elle répète la même erreur à chaque partie. La
   même formule qui tire au sort en gagne **18 %**, comme le jeu aléatoire. L'entraînement part donc d'un niveau
   décent et peut grimper, au lieu de piétiner dans une zone où tout se vaut.

Concrètement, la probabilité de jouer un coup est proportionnelle à `exp(note)`. Des poids tous à zéro donnent un
tirage uniforme (jeu aléatoire) ; plus les poids grandissent, plus l'IA devient tranchée. L'entraînement apprend
donc à la fois **quoi** préférer et **à quel point** y tenir.

Une politique se range dans un fichier JSON lisible à l'œil nu : on peut l'ouvrir, lire les poids, les corriger
à la main, et rejouer. C'est voulu — un agent qu'on ne peut pas inspecter est un agent qu'on ne peut pas guider.
"""
import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from src.core.ai.features import FEATURE_COUNT, FEATURE_NAMES, describe_weights, feature_vector, weights_as_dict
from src.core.ai.opponent import Pick, legal_picks
from src.core.domain.game import Game

FORMAT_VERSION = 1


@dataclass
class LinearPolicy:
    """Une IA = un vecteur de poids, un par critère."""
    weights: List[float] = field(default_factory=lambda: [0.0] * FEATURE_COUNT)
    #: Métadonnées d'entraînement, pour savoir d'où sort ce fichier (elles ne changent pas le jeu).
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if len(self.weights) != FEATURE_COUNT:
            raise ValueError(
                f"{len(self.weights)} poids fournis pour {FEATURE_COUNT} critères. "
                f"Un fichier enregistré avant un changement de critères n'est plus relisible : ré-entraîner."
            )

    # ---------------------------------------------------------------- jouer

    def score(self, state: Game, side: str, pick: Pick) -> float:
        features = feature_vector(state, side, pick)
        return sum(weight * value for weight, value in zip(self.weights, features))

    def pick(self, state: Game, side: str, rng: Optional[random.Random] = None,
             greedy: bool = False) -> Pick:
        """
        Le coup joué : tiré au sort parmi les coups jouables, avec une probabilité proportionnelle à `exp(note)`.

        `greedy=True` force le coup le mieux noté (utile pour inspecter ce que l'IA « pense », ou pour un
        adversaire d'entraînement figé). En jeu réel on laisse le tirage : il est meilleur, cf. l'en-tête.
        """
        options = legal_picks(state, side)
        if not options:
            raise ValueError("Aucun coup jouable.")
        scores = [self.score(state, side, option) for option in options]

        if greedy or rng is None:
            best = max(range(len(options)), key=lambda index: scores[index])
            return options[best]

        # exp(note) en retirant le maximum d'abord : sans cela, de grands poids font déborder l'exponentielle.
        highest = max(scores)
        weights = [math.exp(score - highest) for score in scores]
        return rng.choices(options, weights=weights, k=1)[0]

    def action_probabilities(self, state: Game, side: str) -> List[Tuple[Pick, float]]:
        """Les coups jouables avec leur probabilité. Sert à expliquer une décision plutôt qu'à jouer."""
        options = legal_picks(state, side)
        scores = [self.score(state, side, option) for option in options]
        highest = max(scores) if scores else 0.0
        weights = [math.exp(score - highest) for score in scores]
        total = sum(weights)
        return sorted(zip(options, [weight / total for weight in weights]),
                      key=lambda pair: pair[1], reverse=True)

    # ------------------------------------------------------------- fichiers

    def to_dict(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "features": FEATURE_NAMES,
            "weights": weights_as_dict(self.weights),
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LinearPolicy":
        names = data.get("features", FEATURE_NAMES)
        if list(names) != FEATURE_NAMES:
            raise ValueError(
                "Ce fichier d'IA a été produit avec d'autres critères que ceux du code actuel "
                f"(fichier : {list(names)}). Ré-entraîner pour repartir sur les critères courants."
            )
        weights = data["weights"]
        ordered = [float(weights[name]) for name in FEATURE_NAMES]
        return cls(weights=ordered, meta=data.get("meta", {}))

    def save(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w") as file:
            json.dump(self.to_dict(), file, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "LinearPolicy":
        with open(path, "r") as file:
            return cls.from_dict(json.load(file))

    # ------------------------------------------------------------- lisible

    def explain(self, top: int = 6) -> str:
        return describe_weights(self.weights, top=top)


def random_policy(rng: random.Random, scale: float = 1.0) -> LinearPolicy:
    """Une IA aux poids tirés au hasard. Sert aux tests ; **pas** un bon point de départ d'entraînement
    (cf. `train.py` : on part de poids nuls, qui donnent le jeu aléatoire)."""
    return LinearPolicy(weights=[rng.gauss(0.0, scale) for _ in range(FEATURE_COUNT)])


def policy_strategy(policy: LinearPolicy):
    """
    Emballe une politique pour qu'elle ait la même signature que `random_pick` / `heuristic_pick`, et puisse
    donc servir d'adversaire dans l'arène comme dans `/ai_pick`.
    """
    def strategy(game: Game, side: str, rng: random.Random) -> Pick:
        return policy.pick(game, side, rng)
    return strategy


def from_weights(values: Sequence[float], meta: Optional[dict] = None) -> LinearPolicy:
    return LinearPolicy(weights=list(values), meta=dict(meta or {}))
