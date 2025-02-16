import logging
import traceback
from typing import Any, Dict, List

from fastapi.responses import JSONResponse
from src.schemas.game_schemas import PlayerCards, ProcessRoundInput
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Body, Request
from src.core.services.game_service import create_game, process_round_service, init_game_from_template, save_for_test_service
from src.utils.config import BASE_DIR

# logging.basicConfig(level=logging.DEBUG)
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Assure l'affichage dans le terminal
)

app = FastAPI(debug=True)

# Configuration du middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL (changer si nécessaire)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    try:
        print("DEBUG: Middleware appelé pour", request.url)
        return await call_next(request)
    except Exception as exc:
        logging.error(f"Erreur capturée pour {request.url}: {exc}")
        traceback.print_exc()  # Affiche la trace complète
        return JSONResponse(
            status_code=500,
            content={"detail": "Erreur interne. Consultez les logs pour plus d'informations."},
        )


# Gestionnaire global des erreurs
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Erreur globale pour {request.url}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur inattendue. Consultez les logs pour plus d'informations."},
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
def init_game(players_cards: PlayerCards = Body(...)) -> Dict[str, Any]:
    """
    Initialise une partie avec les cartes fournies pour deux joueurs.
    """
    try:
        # Créer une partie avec les données validées
        game = create_game(players_cards)

        # Retourner la partie initialisée
        return {"status": "success", "game": game.to_dict()}
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
        print("DEBUG: Erreur dans save_for_test_service:", e)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Game ID '{game_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
