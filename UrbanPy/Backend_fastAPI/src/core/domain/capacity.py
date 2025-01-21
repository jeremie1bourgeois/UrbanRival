class Capacity:
    def __init__(self, target: str, type: str, value: int, borne: int, how: str = "", condition_effect: str = "", lvl_priority: int = 0):
        self.target = target # ally, enemy
        self.type = type # power, damage, attack, pillz, life, poison, heal || ability, bonus
        self.value = value
        self.how = how # support, Growth, Degrowth, Equalizer, Brawl || stop, copy, protection, cancel
        self.borne = borne
        self.condition_effect = condition_effect
        self.lvl_priority = lvl_priority
        
        # stop: puissance et degat +2
        # condition_effect: stop ; target: ally ; type = "puissance_dommage" ; value = 2

    @classmethod
    def from_dict(cls, data: dict) -> 'Capacity':
        """
        Crée une instance de Capacity à partir d'un dictionnaire.
        """
        return cls(
            target=str(data.get("target", "")),
            type=str(data.get("type", "")),
            value=int(data.get("value", 0)),
            how=str(data.get("how", "")),
            borne=int(data.get("borne", 0)) if data.get("borne") is not None else 0,
            condition_effect=str(data.get("condition_effect", "")),
            lvl_priority=int(data.get("lvl_priority", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "type": self.type,
            "value": self.value,
            "how": self.how,
            "borne": self.borne,
            "condition_effect": self.condition_effect,
            "lvl_priority": self.lvl_priority,
        }