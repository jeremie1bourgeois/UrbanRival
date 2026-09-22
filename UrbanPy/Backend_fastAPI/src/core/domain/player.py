# src/core/domain/player.py
from typing import List
from src.core.domain.card import Card
from src.core.domain.effect import PersistentEffect

class Player:
    def __init__(self, name: str = "", life: int = -1, pillz: int = -1,
                 cards: List[Card] = None, effect_list: List[PersistentEffect] = None,
                 start_life: int = None, start_pillz: int = None):
        self.name = name
        self.life = life
        self.pillz = pillz
        # Situation de départ de la partie, figée : « Par Vie / Pillz perdue » compte l'écart avec elle (REGLES 3.14).
        self.start_life = life if start_life is None else start_life
        self.start_pillz = pillz if start_pillz is None else start_pillz
        self.cards = cards if cards is not None else []
        self.effect_list = effect_list if effect_list is not None else []

    @staticmethod
    def from_dict_template(data: dict) -> "Player":
        player = Player()
        player.name = data.get("name", "")
        player.life = data.get("life", 0)
        player.pillz = data.get("pillz", 0)
        # Anciennes sauvegardes (avant 2026-09-22) : la partie démarrait à 12 vies et 12 pillz.
        player.start_life = data.get("start_life", 12)
        player.start_pillz = data.get("start_pillz", 12)
        player.cards = [Card.from_dict_template(card) for card in data.get("cards", [])]
        player.effect_list = [PersistentEffect.from_dict(effect) for effect in data.get("effect_list", [])]
        return player

    def to_dict(self):
        return {
            "name": self.name,
            "life": self.life,
            "pillz": self.pillz,
            "start_life": self.start_life,
            "start_pillz": self.start_pillz,
            "cards": [card.to_dict() for card in self.cards],
            "effect_list": [effect.to_dict() for effect in self.effect_list],
        }

    def __repr__(self):
        return f"Player(name={self.name}, life={self.life}/{self.start_life}, pillz={self.pillz}/{self.start_pillz}, cards={self.cards}, effect_list={self.effect_list})"
