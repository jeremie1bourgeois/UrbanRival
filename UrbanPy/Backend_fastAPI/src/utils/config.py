import os
from typing import List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Le front servi par Vite en développement ; ailleurs, le déploiement déclare ses origines.
FRONT_DEV_ORIGIN = "http://localhost:5173"


def cors_origins() -> List[str]:
    """Origines autorisées à appeler l'API, lues dans `UR_CORS_ORIGINS` (séparées par des virgules)."""
    declarees = os.environ.get("UR_CORS_ORIGINS", "").split(",")
    return [origine.strip() for origine in declarees if origine.strip()] or [FRONT_DEV_ORIGIN]
