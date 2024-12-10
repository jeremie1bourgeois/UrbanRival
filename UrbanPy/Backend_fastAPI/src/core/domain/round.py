from pydantic import BaseModel
from typing import Optional

class Ally(BaseModel):
    card_index: Optional[int] = None
    win: bool = False

class Enemy(BaseModel):
    card_index: Optional[int] = None
    win: bool = False

class Round(BaseModel):
    ally: Ally = Ally()
    enemy: Enemy = Enemy()
