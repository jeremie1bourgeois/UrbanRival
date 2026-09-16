# src/core/domain/player.py
from typing import List
from src.core.domain.card import Card
from src.core.domain.effect import PersistentEffect

class Player:
    def __init__(self, name: str = "", life: int = -1, pillz: int = -1,
                 cards: List[Card] = None, effect_list: List[PersistentEffect] = None):
        self.name = name
        self.life = life
        self.pillz = pillz
        self.cards = cards if cards is not None else []
        self.effect_list = effect_list if effect_list is not None else []

    @staticmethod
    def from_dict_template(data: dict) -> "Player":
        player = Player()
        player.name = data.get("name", "")
        player.life = data.get("life", 0)
        player.pillz = data.get("pillz", 0)
        player.cards = [Card.from_dict_template(card) for card in data.get("cards", [])]
        player.effect_list = [PersistentEffect.from_dict(effect) for effect in data.get("effect_list", [])]
        return player

    def to_dict(self):
        return {
            "name": self.name,
            "life": self.life,
            "pillz": self.pillz,
            "cards": [card.to_dict() for card in self.cards],
            "effect_list": [effect.to_dict() for effect in self.effect_list],
        }

    def __repr__(self):
        return f"Player(name={self.name}, life={self.life}, pillz={self.pillz}, cards={self.cards}, effect_list={self.effect_list})"
