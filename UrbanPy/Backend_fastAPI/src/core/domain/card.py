# src/core/domain/card.py
import json
import os

from src.core.domain.capacity import Capacity

class Card:
    
    def __init__(self, card_name: str, nb_stars: int = 1):
        """
        Initialise une carte à partir de son nom et de son nombre d'étoiles.
        Charge les données depuis un fichier JSON.
        """
        # Chemin codé en dur vers le fichier JSON
        json_path = "../data/jsonData_officiel.json"

        # Vérifier que le fichier JSON existe
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found at path: {json_path}")

        # Charger les données du fichier JSON
        with open(json_path, "r") as file:
            data = json.load(file)

        # Rechercher la carte correspondant au nom donné
        matching_keys = [key for key in data.keys() if key.lower() == card_name.lower()]
        if not matching_keys:
            raise ValueError(f"No card found with name: {card_name}")

        # Récupérer les données de la carte
        card_data = data[matching_keys[0]]

        # Récupérer les données correspondant au nombre d'étoiles
        star_data = card_data.get(str(nb_stars), None)
        if not star_data:
            raise ValueError(f"No data for {nb_stars} stars for card: {card_name}")

        # Initialiser les attributs de la carte
        self.name: str = matching_keys[0]
        self.faction: str = card_data.get("faction", "")
        self.starOff: int = card_data.get("starOff", 0)
        self.bonus: str = card_data.get("bonus", "")
        self.stars: int = nb_stars
        self.power: int = int(star_data.get("power", 0))
        self.damage: int = int(star_data.get("damage", 0))
        self.ability: str = star_data.get("ability", "")
        
        self.bonus_description: str = []
        self.ability_description: str = []
        
        self.power_fight: int = 0
        self.damage_fight: int = 0
        self.ability_fight: str = ""
        self.bonus_fight: str = ""
        self.pillz_fight: int = 0
        self.fury: bool = False
        
        self.attack: int = 0
        self.played: bool = False
        self.win: bool = False
    
    @staticmethod
    def from_dict_template(data: dict) -> "Card":
        
        card = Card.__new__(Card)
        card.name = data.get("name")
        card.faction = data.get("faction")
        card.starOff = data.get("starOff")
        card.bonus = Capacity.from_dict(data.get("bonus"))
        card.stars = data.get("stars")
        card.power = data.get("power")
        card.damage = data.get("damage")
        card.ability = Capacity.from_dict(data.get("ability"))
        
        card.bonus_description = data.get("bonus_description")
        card.ability_description = data.get("ability_description")
        
        card.pillz_fight = data.get("pillz_fight")
        card.attack = data.get("attack")
        card.played = data.get("played")

        card.power_fight = data.get("power_fight")
        card.damage_fight = data.get("damage_fight")
        card.ability_fight = data.get("ability_fight")
        card.bonus_fight = data.get("bonus_fight")
        card.win = data.get("win")
        return card

    @staticmethod
    def from_dict(data: dict) -> "Card":
        card_name = data.get("name", "")
        nb_stars = data.get("stars", 1)

        card = Card(card_name=card_name, nb_stars=nb_stars)
        card.power_fight = data.get("power_fight", 0)
        card.damage_fight = data.get("damage_fight", 0)
        card.ability_fight = data.get("ability_fight", "")
        card.bonus_fight = data.get("bonus_fight", "")
        card.pillz_fight = data.get("pillz_fight", 0)
        card.attack = data.get("attack", 0)
        card.played = data.get("played", 0)
        return card

    def to_dict(self) -> dict:
        """
        Convertit la carte en dictionnaire JSON-serializable.
        """
        return {
            "name": self.name,
            "faction": self.faction,
            "starOff": self.starOff,
            "bonus": self.bonus.to_dict() if self.bonus else None,
            "stars": self.stars,
            "power": self.power,
            "damage": self.damage,
            "ability": self.ability.to_dict() if self.ability else None,
            "bonus_description": self.bonus_description,
            "ability_description": self.ability_description,
            "pillz_fight": self.pillz_fight,
            "attack": self.attack,
            "played": self.played,
            "power_fight": self.power_fight,
            "damage_fight": self.damage_fight,
            "ability_fight": self.ability_fight.to_dict() if self.ability_fight else None,
            "bonus_fight": self.bonus_fight.to_dict() if self.bonus_fight else None,
            "win": self.win,
        }