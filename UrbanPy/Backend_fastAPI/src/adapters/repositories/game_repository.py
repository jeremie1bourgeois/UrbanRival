from src.core.domain.game import Game
from typing import Dict
import json
import os

def get_new_game_id(directory="data/game") -> int:
    os.makedirs(directory, exist_ok=True)
    dirs = [f for f in os.listdir(directory) if f.startswith("game_")]
    next_id = max([int(f.split("_")[1]) for f in dirs] + [0]) + 1
    return next_id

def save_game_to_json(game: Game, game_id: int, game_directory: str):
    # Créer le nom du fichier avec le nombre de tours
    filename = f"game_data_{game_id}_{game.nb_turn}.json"
    filepath = os.path.join(game_directory, filename)

    # Créer le dossier s'il n'existe pas
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as file:
        res = game.to_dict()
        json.dump(res, file, indent=4)

def load_game_from_json(file_path: str) -> Game:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Game file not found: {file_path}")
    with open(file_path, "r") as file:
        data = json.load(file)
    return Game.from_dict_template(data)