# src/core/domain/game.py
from typing import List
from src.core.domain.round import Round
from src.core.domain.player import Player

class Game:
    def __init__(self, nb_turn: int = 0, turn: bool = True, ally: Player = Player(), enemy: Player = Player(), history: List[Round] = []):
        self.nb_turn: int = nb_turn
        self.turn: bool = turn
        self.ally: Player = ally
        self.enemy: Player = enemy
        self.history: List[Round] = history

    @staticmethod
    def from_dict(data):
        game = Game()
        game.nb_turn = data.get("nb_turn", 0)
        game.turn = data.get("turn", True)
        game.ally = Player.from_dict(data["ally"])
        game.enemy = Player.from_dict(data["enemy"])
        game.history = [Round(**round_data) for round_data in data.get("history", [])]
        return game
    
    @staticmethod
    def from_dict_template(data):
        game = Game()
        game.nb_turn = data.get("nb_turn", 0)
        game.turn = data.get("turn", True)
        game.ally = Player.from_dict_template(data["ally"])
        game.enemy = Player.from_dict_template(data["enemy"])
        game.history = [Round(**round_data) for round_data in data.get("history", [])]
        return game

    def to_dict(self):
        return {
            "nb_turn": self.nb_turn,
            "turn": self.turn,
            "ally": self.ally.to_dict(),
            "enemy": self.enemy.to_dict(),
            "history": [round_instance.model_dump() for round_instance in self.history],
        }
