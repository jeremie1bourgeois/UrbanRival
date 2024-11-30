# src/core/domain/player.py
from typing import List, Tuple, Any
from src.core.domain.card import Card

class Player:
    def __init__(self, name: str = "", life: int = -1, pillz: int = -1,
                 cards: List[Card] = None, effect_list: List[Tuple[Any, int, int]] = None):
        self.name = name
        self.life = life
        self.pillz = pillz
        self.cards = cards if cards is not None else []
        self.effect_list = effect_list if effect_list is not None else []

    @staticmethod
    def from_dict(data: dict) -> "Player":
        player = Player()
        player.name = data.get("name", "")
        player.life = data.get("life", 0)
        player.pillz = data.get("pillz", 0)
        player.cards = [Card.from_dict(card) for card in data.get("cards", [])]
        player.effect_list = data.get("effect_list", [])
        return player

    def to_dict(self):
        return {
            "name": self.name,
            "life": self.life,
            "pillz": self.pillz,
            "cards": [card.to_dict() for card in self.cards],
            "effect_list": self.effect_list,
        }
