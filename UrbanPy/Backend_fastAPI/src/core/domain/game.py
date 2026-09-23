from typing import List
from src.core.domain.round import Round
from src.core.domain.player import Player

NB_ROUNDS = 4  # nombre de rounds d'une partie

class Game:
    """Une partie : deux joueurs, le round en cours, l'historique des rounds joués."""

    def __init__(self, nb_turn: int = 0, turn: bool = True, ally: Player = None, enemy: Player = None, history: List[Round] = None,
                 night: bool = False):
        self.nb_turn: int = nb_turn  # numéro du round en cours (1 = premier round) ; vaut NB_ROUNDS + 1 quand la partie est finie
        self.turn: bool = turn
        self.night: bool = night   # tiré au sort à la création : les cartes portent alors leurs textes « Night: »
        self.ally: Player = ally if ally is not None else Player()
        self.enemy: Player = enemy if enemy is not None else Player()
        self.history: List[Round] = history if history is not None else []

    @staticmethod
    def from_dict_template(data: dict) -> "Game":
        game = Game()
        game.nb_turn = data.get("nb_turn", 0)
        game.turn = data.get("turn", True)
        game.night = data.get("night", False)
        game.ally = Player.from_dict_template(data["ally"])
        game.enemy = Player.from_dict_template(data["enemy"])
        game.history = [Round(**round_data) for round_data in data.get("history", [])]
        return game

    def to_dict(self) -> dict:
        return {
            "nb_turn": self.nb_turn,
            "turn": self.turn,
            "night": self.night,
            "ally": self.ally.to_dict(),
            "enemy": self.enemy.to_dict(),
            "history": [round_instance.model_dump() for round_instance in self.history],
        }
    
    def __repr__(self) -> str:
        return f"Game(nb_turn={self.nb_turn}, turn={self.turn}, night={self.night}, ally={self.ally}, enemy={self.enemy}, history={self.history})"
