# src/core/domain/card.py
from src.adapters.repositories.card_repository import get_official_card
from src.core.domain.capacity import Capacity
from src.core.parsing.capacity_parser import parse_capacity


# Emplacements de combat d'une carte jouée : son ability, son bonus, et l'ability « Team: » du Leader de l'équipe
FIGHT_SLOTS = ("ability_fight", "bonus_fight", "leader_fight")


class Card:

    def __init__(self, card_name: str, nb_stars: int = 1):
        """
        Initialise une carte à partir de son nom et de son nombre d'étoiles (données officielles scrapées).
        Les abilities / bonus sont parsés en Capacity ; None si absents ou non gérés par le moteur.
        """
        name, card_data = get_official_card(card_name)
        star_data = card_data.get(str(nb_stars))
        if not star_data:
            raise ValueError(f"No data for {nb_stars} stars for card: {card_name}")

        self.name: str = name
        self.faction: str = card_data.get("faction", "")
        self.starOff: int = card_data.get("starOff", 0)
        self.stars: int = nb_stars
        self.power: int = int(str(star_data.get("power", 0)).strip())
        self.damage: int = int(str(star_data.get("damage", 0)).strip())

        self.image: str = star_data.get("image", "")          # illustration de la carte à ce niveau (URL CDN)
        self.clan_image: str = card_data.get("clan_image", "")

        self.bonus_description: str = card_data.get("bonus", "").strip()
        self.ability_description: str = star_data.get("ability", "").strip()
        self.bonus: Capacity = parse_capacity(self.bonus_description).capacity
        self.ability: Capacity = parse_capacity(self.ability_description).capacity

        self.power_fight: int = 0
        self.damage_fight: int = 0
        self.ability_fight: Capacity = None
        self.bonus_fight: Capacity = None
        self.leader_fight: Capacity = None
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
        card.bonus = Capacity.from_dict(data["bonus"]) if data.get("bonus") else None
        card.stars = data.get("stars")
        card.power = data.get("power")
        card.damage = data.get("damage")
        card.ability = Capacity.from_dict(data["ability"]) if data.get("ability") else None

        card.image = data.get("image", "")
        card.clan_image = data.get("clan_image", "")

        card.bonus_description = data.get("bonus_description")
        card.ability_description = data.get("ability_description")

        card.pillz_fight = data.get("pillz_fight")
        card.fury = data.get("fury", False)
        card.attack = data.get("attack")
        card.played = data.get("played")

        card.power_fight = data.get("power_fight")
        card.damage_fight = data.get("damage_fight")
        card.ability_fight = Capacity.from_dict(data.get("ability_fight")) if data.get("ability_fight") else None
        card.bonus_fight = Capacity.from_dict(data.get("bonus_fight")) if data.get("bonus_fight") else None
        card.leader_fight = Capacity.from_dict(data.get("leader_fight")) if data.get("leader_fight") else None
        card.win = data.get("win")
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
            "image": self.image,
            "clan_image": self.clan_image,
            "bonus_description": self.bonus_description,
            "ability_description": self.ability_description,
            "pillz_fight": self.pillz_fight,
            "fury": self.fury,
            "attack": self.attack,
            "played": self.played,
            "power_fight": self.power_fight,
            "damage_fight": self.damage_fight,
            "ability_fight": self.ability_fight.to_dict() if self.ability_fight else None,
            "bonus_fight": self.bonus_fight.to_dict() if self.bonus_fight else None,
            "leader_fight": self.leader_fight.to_dict() if self.leader_fight else None,
            "win": self.win,
        }

    # print les données de fight + attack
    def __repr__(self) -> str:
        return f"Card(name={self.name}, power_fight={self.power_fight}, damage_fight={self.damage_fight}, attack={self.attack}, played={self.played}, win={self.win})"
