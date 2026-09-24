"""Cache local des images de cartes.

Le front ne demande ses images qu'au backend : chaque illustration est téléchargée une seule fois
depuis le CDN d'Urban Rivals, puis relue sur disque. Seules les images citées par le catalogue
officiel sont servies — l'endpoint ne doit pas pouvoir rapatrier une URL quelconque.
"""
import os
import urllib.request
from functools import lru_cache
from typing import Dict

from src.adapters.repositories.card_repository import all_image_urls
from src.utils.config import BASE_DIR

CACHE_DIR = os.path.join(BASE_DIR, "data", "card_images")
DOWNLOAD_TIMEOUT_SECONDS = 20


@lru_cache(maxsize=1)
def cdn_url_by_filename() -> Dict[str, str]:
    """Nom de fichier servi par l'API → URL d'origine sur le CDN (les noms sont uniques)."""
    return {url.rsplit("/", 1)[-1]: url for url in all_image_urls()}


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return response.read()


def cached_image_path(filename: str) -> str:
    """Chemin local de l'image, téléchargée si le cache ne l'a pas encore.

    ValueError si l'image n'est pas au catalogue, OSError si le CDN ne répond pas.
    """
    url = cdn_url_by_filename().get(filename)
    if url is None:
        raise ValueError(f"Unknown card image: {filename}")

    chemin = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(chemin):
        contenu = _download(url)
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Écriture par un fichier temporaire : deux requêtes simultanées ne doivent pas laisser un PNG tronqué.
        provisoire = f"{chemin}.part"
        with open(provisoire, "wb") as fichier:
            fichier.write(contenu)
        os.replace(provisoire, chemin)
    return chemin
