from src.core.domain.game import Game
from typing import Dict
import json
import os

def get_new_game_id(directory="data/game") -> int:
	os.makedirs(directory, exist_ok=True)
	files = [f for f in os.listdir(directory) if f.startswith("game_data_") and f.endswith(".json")]
	next_id = max([int(f.split("_")[2].split(".")[0]) for f in files] + [0]) + 1
	return next_id

def save_game_to_json(game: Game, game_id: int):
    filepath = os.path.join("data", "game", f"game_data_{game_id}.json")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as file:
        json.dump(game.to_dict(), file, indent=4)

def load_game_from_json(file_path: str) -> Game:
    print(f"Loading game from: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Game file not found: {file_path}")
    with open(file_path, "r") as file:
        data = json.load(file)
    print(f"Game loaded: {data}")
    return Game.from_dict_template(data)
