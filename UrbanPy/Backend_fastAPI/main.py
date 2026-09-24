import logging
import os
import sys
from typing import Any, Dict, List

from fastapi.responses import FileResponse, JSONResponse
from src.schemas.game_schemas import GameSetup, ProcessRoundInput
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Body, Request
from src.core.services.game_service import create_game, process_round_service, init_game_from_template, save_for_test_service
from src.adapters.repositories.card_image_cache import cached_image_path
from src.adapters.repositories.card_repository import official_card_catalogue
from src.utils.config import cors_origins

logging.basicConfig(
    level=os.environ.get("UR_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Assure l'affichage dans le terminal
)

app = FastAPI()

# Origines autorisées : le front local par défaut, `UR_CORS_ORIGINS` pour un autre déploiement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logging.exception("Erreur capturée pour %s : %s", request.url, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erreur interne. Consultez les logs pour plus d'informations."},
        )


@app.post("/process_round/{game_id}", response_model=Dict[str, Any])
def process_game_round(game_id: str, round_data: ProcessRoundInput = Body(...)):
    """
    Traite un round de jeu en utilisant les données fournies.
    """
    try:
        # Appeler le service en passant l'objet round_data
        (updated_game, state) = process_round_service(game_id, round_data)

        return {"status": "success", "game": updated_game.to_dict(), "state": state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Game ID '{game_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/init_game/", response_model=Dict[str, Any])
def init_game(setup: GameSetup = Body(...)) -> Dict[str, Any]:
    """
    Initialise une partie avec les cartes fournies pour deux joueurs, dans la situation de départ demandée
    (vies, pillz, premier joueur — voir GameSetup).
    """
    try:
        # Créer une partie avec les données validées
        (game, new_id) = create_game(setup)

        # Retourner la partie initialisée
        return {"status": "success", "game": game.to_dict(), "game_id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/init_game/template", response_model=Dict[str, Any])
def init_game_template() -> Dict[str, Any]:
    """
    Initialise une partie à partir d'un template JSON prédéfini.
    """
    try:
        # Initialiser la partie depuis le template
        (game, new_id) = init_game_from_template()

        # Retourner la partie initialisée
        return {"status": "success", "game": game.to_dict(), "game_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cards", response_model=List[Dict[str, Any]])
def cards_catalogue() -> List[Dict[str, Any]]:
    """
    Catalogue des cartes officielles (clan, niveaux, power/damage/ability par niveau, pouvoirs gérés ou non),
    pour composer un deck côté front.
    """
    return official_card_catalogue()


@app.get("/card_image/{filename}")
def card_image(filename: str) -> FileResponse:
    """
    Sert une illustration du catalogue depuis le cache local, en la rapatriant du CDN d'Urban Rivals
    à la première demande. Le front passe donc par le backend et ne dépend plus du CDN.
    """
    try:
        return FileResponse(cached_image_path(filename), media_type="image/png")
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown card image: {filename}")
    except OSError as e:
        raise HTTPException(status_code=502, detail=f"Image unavailable on the CDN: {e}")


@app.get("/save_for_test")
def save_for_test(game_id: int) -> Dict[str, Any]:
    """
    Crée une sauvegarde d'une situation A d'une partie, d'un play des joueurs et de la situation B qui en découle.
    (Est appelé lorsque un round s'est déroulé comme prévue et que l'on souhaite sauvegarder les données pour les tests.)
    """
    try:
        # Sauvegarder les données pour les tests
        save_for_test_service(game_id)
        
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Game ID '{game_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
