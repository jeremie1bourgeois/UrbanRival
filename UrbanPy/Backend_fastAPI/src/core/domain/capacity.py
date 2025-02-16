class Capacity:
    def __init__(self, target: str, types: list[str], value: int, borne: int, how: str = "", effect_conditions: list[str] = [], lvl_priority: int = 0):
        self.target = target # ally, enemy
        self.types = types # [ power, damage, power_damage, attack, pillz, life, pillz_life || ability, bonus ]
        self.value = value
        self.how = how # support, Growth, Degrowth, Equalizer, Brawl || stop, copy, protection, cancel || toxin, poison, regen, heal, ??, dope
        self.borne = borne
        self.effect_conditions = effect_conditions # [ Revenge, Reprisal, Confidence, Courage, Symmetry, Asymmetry, Bet ] # bool bool bool bool bool bool bool var// une var
        self.lvl_priority = lvl_priority

        # stop: puissance et degat +2
        # effect_conditions: stop ; target: ally ; type = "puissance_dommage" ; value = 2
    
    def __str__(self) -> str:
        return f"Capacity(target={self.target}, types={self.types}, value={self.value}, how={self.how}, borne={self.borne}, effect_conditions={self.effect_conditions}, lvl_priority={self.lvl_priority})"

    @classmethod
    def from_dict(cls, data: dict) -> 'Capacity':
        """
        Crée une instance de Capacity à partir d'un dictionnaire.
        """
        return cls(
            target=str(data.get("target", "")),
            types=data.get("types", []),
            value=int(data.get("value", 0)),
            how=str(data.get("how", "")),
            borne=int(data.get("borne", 0)) if data.get("borne") is not None else 0,
            effect_conditions=data.get("effect_conditions", []),
            lvl_priority=int(data.get("lvl_priority", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "types": self.types,
            "value": self.value,
            "how": self.how,
            "borne": self.borne,
            "effect_conditions": self.effect_conditions,
            "lvl_priority": self.lvl_priority,
        }