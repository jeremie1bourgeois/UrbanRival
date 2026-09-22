from enum import Enum
from pydantic import BaseModel, ValidationInfo, field_validator, validator
from typing import List, Dict, Literal, Optional, Tuple, Union
from pydantic import Field

from src.core.domain.round import Round


class CardInput(BaseModel):
    card_name: str
    nb_stars: int = 1  # Par défaut : 1 étoile

    @validator("nb_stars")
    def validate_nb_stars(cls, nb_stars):
        if not (1 <= nb_stars <= 5):
            raise ValueError("Number of stars must be between 1 and 5.")
        return nb_stars


class PlayerCards(BaseModel):
	player1: List[CardInput] = Field(..., min_items=4, max_items=4)
	player2: List[CardInput] = Field(..., min_items=4, max_items=4)
	night: Optional[bool] = None   # None : jour ou nuit tiré au sort à la création de la partie

	@validator("player1", "player2")
	def validate_card_list_length(cls, cards):
		if len(cards) != 4:
			raise ValueError("Each player must have exactly 4 cards.")
		return cards


class GameSetup(PlayerCards):
	"""
	Corps de `/init_game/` : les mains, et la situation de départ qui distingue un mode de jeu — vies et pillz
	(une valeur pour les deux joueurs, ou `[joueur 1, joueur 2]` : en Survivor ils ne partent pas à égalité)
	et le premier joueur du round 1 (`random` : tiré au sort, comme sur le site).
	"""
	life: Union[int, List[int]] = 12
	pillz: Union[int, List[int]] = 12
	first: Literal["player1", "player2", "random"] = "player1"

	@field_validator("life", "pillz")
	@classmethod
	def validate_values(cls, values, info: ValidationInfo):
		pair = [values, values] if isinstance(values, int) else list(values)
		if len(pair) != 2:
			raise ValueError(f"{info.field_name} must be one value or [player 1, player 2].")
		if any(value < (1 if info.field_name == "life" else 0) for value in pair):
			raise ValueError(f"{info.field_name} values are too low.")
		return values

	def per_side(self, values) -> Tuple[int, int]:
		return (values, values) if isinstance(values, int) else (values[0], values[1])


class CardSchema(BaseModel):
	name: str
	faction: str = ""
	bonus: str = ""
	stars: int = 0
	power: int = 0
	damage: int = 0
	ability: str = ""


class GameSchema(BaseModel):
	nb_turn: int
	turn: bool
	ally: Dict[str, List[CardSchema]]
	enemy: Dict[str, List[CardSchema]]
	history: List[Round]

class GameResult(Enum):
    ALLY = "Ally Wins"
    ENEMY = "Enemy Wins"
    DRAW = "Draw"
    NONE = "Game Not Finished"

class ProcessRoundInput(BaseModel):
    player1_card_index: int
    player1_pillz: int
    player1_fury: bool = False
    
    player2_card_index: int
    player2_pillz: int
    player2_fury: bool = False

    @classmethod
    def validate_pillz_and_indices(cls, values):
        if values["player1_pillz"] < 0 or values["player2_pillz"] < 0:
            raise ValueError("Pillz values must be non-negative.")
        if values["player1_card_index"] < 0 or values["player2_card_index"] < 0:
            raise ValueError("Card indices must be non-negative.")
        return values
