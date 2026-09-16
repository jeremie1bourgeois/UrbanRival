from pydantic import BaseModel
from typing import List, Optional

class Ally(BaseModel):
    card_index: Optional[int] = None
    win: bool = False

class Enemy(BaseModel):
    card_index: Optional[int] = None
    win: bool = False

class Round(BaseModel):
    ally: Ally = Ally()
    enemy: Enemy = Enemy()
    log: List[dict] = []   # journal des effets du round (voir src/core/domain/journal.py)
