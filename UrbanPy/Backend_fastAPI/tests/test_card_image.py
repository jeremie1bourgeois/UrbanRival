"""Le backend sert les images de cartes depuis un cache local : le CDN d'Urban Rivals n'est
appelé qu'à la première demande d'une image, et seules les images du catalogue sont servies."""
import pytest
from fastapi.testclient import TestClient

import src.adapters.repositories.card_image_cache as card_image_cache
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(card_image_cache, "CACHE_DIR", str(tmp_path / "card_images"))
    return TestClient(app)


def une_image_du_catalogue():
    return next(iter(card_image_cache.cdn_url_by_filename().items()))


def test_une_image_est_telechargee_une_fois_puis_relue_du_cache(client, monkeypatch):
    nom, url_cdn = une_image_du_catalogue()
    telechargements = []
    monkeypatch.setattr(card_image_cache, "_download", lambda source: telechargements.append(source) or b"PNG")

    premiere = client.get(f"/card_image/{nom}")
    seconde = client.get(f"/card_image/{nom}")

    assert (premiere.status_code, premiere.content) == (200, b"PNG")
    assert (seconde.status_code, seconde.content) == (200, b"PNG")
    assert telechargements == [url_cdn], "le CDN ne doit être appelé qu'une fois par image"


def test_une_image_hors_catalogue_est_refusee_sans_appeler_le_cdn(client, monkeypatch):
    """Sinon l'endpoint téléchargerait n'importe quelle URL pour le compte du client."""
    monkeypatch.setattr(card_image_cache, "_download",
                        lambda source: pytest.fail(f"téléchargement interdit : {source}"))

    for nom in ("inconnue.png", "../../etc/passwd", "..%2F..%2Fdata%2Fgame"):
        assert client.get(f"/card_image/{nom}").status_code == 404, nom


def test_un_cdn_injoignable_est_signale_au_client(client, monkeypatch):
    nom, _ = une_image_du_catalogue()

    def echoue(source):
        raise OSError("CDN injoignable")

    monkeypatch.setattr(card_image_cache, "_download", echoue)

    assert client.get(f"/card_image/{nom}").status_code == 502
