"""
Branchement de l'IA entraînée dans le jeu : elle devient un adversaire comme les autres.

Le fichier d'une IA entraînée (`data/ai/*.json`) est chargé à la demande et gardé en mémoire. S'il n'existe pas
— cas normal tant qu'aucun entraînement n'a tourné — la stratégie « trained » n'est simplement pas proposée,
plutôt que de faire échouer le serveur au démarrage.

Pour rendre une IA jouable dans l'interface : l'entraîner avec `scripts/train_ai.py --out data/ai/policy.json`,
puis relancer le backend.
"""
import os
import random
from typing import Dict, Optional

from src.core.ai.opponent import Pick
from src.core.ai.policy import LinearPolicy
from src.core.domain.game import Game
from src.utils.config import BASE_DIR

#: Emplacement par défaut de l'IA jouable dans l'interface.
DEFAULT_POLICY_PATH = os.path.join(BASE_DIR, "data", "ai", "policy.json")

_cache: Dict[str, Optional[LinearPolicy]] = {}


def load_policy(path: str = DEFAULT_POLICY_PATH) -> Optional[LinearPolicy]:
    """L'IA entraînée, ou None si le fichier est absent ou illisible (ex. produit avec d'autres critères)."""
    if path not in _cache:
        try:
            _cache[path] = LinearPolicy.load(path)
        except (FileNotFoundError, ValueError, KeyError):
            _cache[path] = None
    return _cache[path]


def forget_cached_policy() -> None:
    """Vide le cache : utile aux tests, et après un ré-entraînement sans redémarrage."""
    _cache.clear()


def trained_pick(game: Game, side: str, rng: random.Random) -> Pick:
    """Stratégie « trained ». Lève une erreur claire si aucune IA n'a encore été entraînée."""
    policy = load_policy()
    if policy is None:
        raise ValueError(
            "Aucune IA entraînée disponible. Lancer d'abord : "
            "python scripts/train_ai.py --out data/ai/policy.json"
        )
    return policy.pick(game, side, rng)


def is_available() -> bool:
    return load_policy() is not None
