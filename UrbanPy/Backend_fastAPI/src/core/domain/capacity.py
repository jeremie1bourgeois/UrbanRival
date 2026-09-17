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
    
    def clone(self) -> "Capacity":
        """
        Copie de combat : les listes (types, conditions) sont dupliquées car le moteur les consomme au fil du round ;
        l'étiquette de journal éventuelle (`label`) est reprise. Bien plus rapide qu'un `deepcopy` — le moteur en
        fait quatre par round, des centaines de milliers dans un solveur.
        """
        copied = Capacity(self.target, list(self.types), self.value, self.borne, self.how,
                          list(self.effect_conditions), self.lvl_priority)
        if hasattr(self, "label"):
            copied.label = self.label
        return copied

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