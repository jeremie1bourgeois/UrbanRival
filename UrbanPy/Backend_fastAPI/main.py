from typing import Any, Dict, List
from src.schemas.game_schemas import PlayerCards, ProcessRoundInput
from fastapi import FastAPI, HTTPException, Body
from src.core.services.game_service import create_game, process_round_service, init_game_from_template
from src.utils.config import BASE_DIR

app = FastAPI()

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
        game = init_game_from_template()

        # Retourner la partie initialisée
        return {"status": "success", "game": game.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
