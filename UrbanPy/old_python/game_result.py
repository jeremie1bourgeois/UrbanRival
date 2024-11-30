from enum import Enum

class GameResult(Enum):
    ALLY = "Ally Wins"
    ENEMY = "Enemy Wins"
    DRAW = "Draw"
    NONE = "Game Not Finished"
