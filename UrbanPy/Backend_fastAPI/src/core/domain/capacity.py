from typing import Optional


class Capacity:
    """
    Capacité d'une ability ou d'un bonus, avant compilation. Le vocabulaire réel (how, types, target,
    effect_conditions) est figé dans src.core.engine.contract (HOWS, TYPES, TARGETS, CONDITIONS) ;
    parse_capacity est la seule source qui construit des Capacity dans ce vocabulaire.
    """

    def __init__(self, target: str, types: list[str], value: int, borne: int, how: str = "",
                effect_conditions: Optional[list[str]] = None, lvl_priority: int = 0):
        self.target = target
        self.types = types
        self.value = value
        self.how = how
        self.borne = borne
        self.effect_conditions = effect_conditions if effect_conditions is not None else []
        self.lvl_priority = lvl_priority

    def __repr__(self) -> str:
        return f"Capacity(target={self.target}, types={self.types}, value={self.value}, how={self.how}, borne={self.borne}, effect_conditions={self.effect_conditions}, lvl_priority={self.lvl_priority})"

    @classmethod
    def from_dict(cls, data: dict) -> 'Capacity':
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