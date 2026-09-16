from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.game import Game
from src.core.use_cases.multipliers import MULTIPLIERS


def apply_capacity_lvl_2(game: Game, card1: Card, card2: Card) -> None:
    """Modificateurs de power / damage / attack : cible ally, puis both, puis enemy, pour chaque emplacement de combat."""
    for apply in (apply_target_ally_effects, apply_target_both_effects, apply_target_enemy_effects):
        for card, opp_card, own, opp in ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally)):
            for slot in FIGHT_SLOTS:
                capacity = getattr(card, slot)
                if capacity is not None:
                    setattr(card, slot, apply(game, own, opp, capacity, card, opp_card))


# Multiplicateurs (champ how) partagés avec le niveau 3
_BONUS_FUNCS = MULTIPLIERS

# Mapping des attributs aussi défini une seule fois
_ATTR_MAP = {
    "attack": "attack",
    "damage": "damage_fight",
    "power": "power_fight"
}

def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "ally":
        return capacity

    # Récupérer tous les attributs correspondants aux types dans capacity.types
    attrs = [_ATTR_MAP.get(type_) for type_ in capacity.types if _ATTR_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne None
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_ally_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus une seule fois
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value = getattr(card1, attr)
                if getattr(card1, attr) < capacity.borne:
                    setattr(card1, attr, min(capacity.borne, current_value + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value = getattr(card1, attr)
                if getattr(card1, attr) > capacity.borne:
                    setattr(card1, attr, max(capacity.borne, current_value + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value = getattr(card1, attr)
            setattr(card1, attr, current_value + bonus)

    return None


def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "enemy":
        return capacity

    # Récupérer tous les attributs correspondants aux types dans capacity.types
    attrs = [_ATTR_MAP.get(type_) for type_ in capacity.types if _ATTR_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne capacity
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_enemy_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus une seule fois
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Appliquer les effets en tenant compte des bornes
    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value = getattr(card2, attr)
                if current_value < capacity.borne:
                    setattr(card2, attr, min(capacity.borne, current_value + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value = getattr(card2, attr)
                if current_value > capacity.borne:
                    setattr(card2, attr, max(capacity.borne, current_value + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value = getattr(card2, attr)
            setattr(card2, attr, current_value + bonus)

    return None


def apply_target_both_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "both":
        return capacity

    # Récupérer tous les attributs correspondants aux types dans capacity.types
    attrs = [_ATTR_MAP.get(type_) for type_ in capacity.types if _ATTR_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne capacity
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_both_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus une seule fois
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Appliquer les effets en tenant compte des bornes
    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value1 = getattr(card1, attr)
                current_value2 = getattr(card2, attr)
                if current_value1 < capacity.borne:  # Vérification pour card1
                    setattr(card1, attr, min(capacity.borne, current_value1 + bonus))
                if current_value2 < capacity.borne:  # Vérification pour card2
                    setattr(card2, attr, min(capacity.borne, current_value2 + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value1 = getattr(card1, attr)
                current_value2 = getattr(card2, attr)
                if current_value1 > capacity.borne:  # Vérification pour card1
                    setattr(card1, attr, max(capacity.borne, current_value1 + bonus))
                if current_value2 > capacity.borne:  # Vérification pour card2
                    setattr(card2, attr, max(capacity.borne, current_value2 + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value1 = getattr(card1, attr)
            current_value2 = getattr(card2, attr)
            setattr(card1, attr, current_value1 + bonus)
            setattr(card2, attr, current_value2 + bonus)

    return None