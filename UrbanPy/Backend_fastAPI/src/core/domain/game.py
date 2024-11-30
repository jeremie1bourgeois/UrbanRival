# src/core/domain/game.py
from typing import List
from src.core.domain.player import Player

class Game:
    def __init__(self, nb_turn: int = 0, turn: bool = True, ally: Player = Player(), enemy: Player = Player(), history: List[str] = []):
        self.nb_turn: int = nb_turn
        self.turn: bool = turn
        self.ally: Player = ally
        self.enemy: Player = enemy
        self.history: List[str] = history

    @staticmethod
    def from_dict(data):
        game = Game()
        game.nb_turn = data.get("nb_turn", 0)
        game.turn = data.get("turn", True)
        game.ally = Player.from_dict(data["ally"])
        game.enemy = Player.from_dict(data["enemy"])
        game.history = []
        return game

    def to_dict(self):
        return {
            "nb_turn": self.nb_turn,
            "turn": self.turn,
            "ally": self.ally.to_dict(),
            "enemy": self.enemy.to_dict(),
            "history": self.history,
        }
