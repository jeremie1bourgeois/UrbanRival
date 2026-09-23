class PersistentEffect:
    """
    Effet actif sur un joueur à la fin de chaque round suivant son activation :
    poison / toxine (vie -value, pas en dessous de borne), heal / regen (vie +value, pas au-dessus de borne),
    dope (pillz +value, pas au-dessus de borne), repair (vie et pillz +value, chacune pas au-dessus de borne),
    consume (pillz -value, pas en dessous de borne), combust (vie et pillz -value, chacune pas en dessous de borne).
    Un effet remplace l'effet de même sorte déjà actif.
    """
    KINDS = ("poison", "toxine", "heal", "regen", "dope", "repair", "consume", "combust")

    def __init__(self, kind: str, value: int, borne: int):
        if kind not in self.KINDS:
            raise ValueError(f"Invalid persistent effect kind: {kind!r}")
        self.kind = kind
        self.value = value
        self.borne = borne

    @classmethod
    def from_dict(cls, data: dict) -> "PersistentEffect":
        return cls(kind=data["kind"], value=int(data["value"]), borne=int(data["borne"]))

    def to_dict(self) -> dict:
        return {"kind": self.kind, "value": self.value, "borne": self.borne}

    def __repr__(self) -> str:
        return f"PersistentEffect(kind={self.kind}, value={self.value}, borne={self.borne})"
