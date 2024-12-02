from pydantic import BaseModel, validator
from typing import List, Dict, Union
from pydantic import Field


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

	@validator("player1", "player2")
	def validate_card_list_length(cls, cards):
		if len(cards) != 4:
			raise ValueError("Each player must have exactly 4 cards.")
		return cards


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
	history: List[str]


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