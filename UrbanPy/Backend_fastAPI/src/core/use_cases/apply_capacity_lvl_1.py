from typing import Tuple, Optional, Set
import copy
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card

def apply_capacity_lvl_1(card1: Card, card2: Card):
    apply_copy(card1, card2)
    apply_stop(card1, card2)
    delete_capacity_protection(card1, card2)

    apply_all_cancel_data_modif(card1, card2)
    apply_all_protect_data_modif(card1, card2)
    
    if card1.ability_fight: card1.ability_fight = apply_exchange_or_copy_data(card1, card2, card1.ability_fight)
    if card1.bonus_fight: card1.bonus_fight = apply_exchange_or_copy_data(card1, card2, card1.bonus_fight)
    if card2.ability_fight: card2.ability_fight = apply_exchange_or_copy_data(card2, card1, card2.ability_fight)
    if card2.bonus_fight: card2.bonus_fight = apply_exchange_or_copy_data(card2, card1, card2.bonus_fight)


def apply_copy(card1: Card, card2: Card):
    if card1.ability_fight and card1.ability_fight.how == "copy":
        if "ability" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_copy_ability(card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_copy_bonus(card2.ability_fight, card1.bonus_fight, card2.bonus_fight)

    if card1.bonus_fight and card1.bonus_fight.how == "copy":
        if "ability" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_copy_ability(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_copy_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
    
    if card2.ability_fight and card2.ability_fight.how == "copy":
        if "ability" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_copy_ability(card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
        elif "bonus" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_copy_bonus(card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
    
    if card2.bonus_fight and card2.bonus_fight.how == "copy":
        if "ability" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_copy_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
        elif "bonus" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_copy_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)

def apply_stop(card1: Card, card2: Card):
    if card1.ability_fight and card1.ability_fight.how == "stop":
        if "ability" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)

    if card1.bonus_fight and card1.bonus_fight.how == "stop":
        if "ability" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)

    if card2.ability_fight and card2.ability_fight.how == "stop":
        if "ability" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_ability(card2.ability_fight, card2.bonus_fight, card1.bonus_fight)
        elif "bonus" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)

    if card2.bonus_fight and card2.bonus_fight.how == "stop":
        if "ability" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight)
        elif "bonus" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)

def delete_capacity_protection(card1: Card, card2: Card) -> None:
    """
    Supprime les capacités qui protègent les autres capacités car les stop ont déjà été appliqués
    """
    capacity_types = ["ability", "bonus"]

    if card1.ability_fight and card1.ability_fight.how == "Protection" and (any(x in card1.ability_fight.types for x in capacity_types)):
        card1.ability_fight = None
    if card1.bonus_fight and card1.bonus_fight.how == "Protection" and (any(x in card1.bonus_fight.types for x in capacity_types)):
        card1.bonus_fight = None
    if card2.ability_fight and card2.ability_fight.how == "Protection" and (any(x in card2.ability_fight.types for x in capacity_types)):
        card2.ability_fight = None
    if card2.bonus_fight and card2.bonus_fight.how == "Protection" and (any(x in card2.bonus_fight.types for x in capacity_types)):
        card2.bonus_fight = None


def apply_all_cancel_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types power/damage/attack
    """
    if card1.ability_fight:
        if card2.ability_fight or card2.bonus_fight:
            (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card1.ability_fight, card2.ability_fight, card2.bonus_fight)
    if card1.bonus_fight:
        if card2.ability_fight or card2.bonus_fight:
            (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card1.bonus_fight, card2.ability_fight, card2.bonus_fight)
    if card2.ability_fight:
        if card1.ability_fight or card1.bonus_fight:
            (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card2.ability_fight, card1.ability_fight, card1.bonus_fight)
    if card2.bonus_fight:
        if card1.ability_fight or card1.bonus_fight:
            (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card2.bonus_fight, card1.ability_fight, card1.bonus_fight)


# Constantes globales
LIST_HOW_NOT_CANCEL: Set[str] = {"cancel", "stop", "copy", "Protection"}
TYPES_TO_CHECK: list[str] = ["power", "damage", "attack", "life", "pillz"]

def should_cancel_capacity(opp_capacity: Optional[Capacity], type_: str) -> bool:
    """
    Vérifie si une capacité adverse doit être annulée pour un type donné.
    """
    return (opp_capacity and 
            type_ in opp_capacity.types and 
            opp_capacity.how not in LIST_HOW_NOT_CANCEL)

def process_type(capacity: Capacity, 
                capacity_opp_1: Optional[Capacity], 
                capacity_opp_2: Optional[Capacity],
                type_: str) -> Tuple[Optional[Capacity], Optional[Capacity]]:
    if type_ not in capacity.types:
        return capacity_opp_1, capacity_opp_2
        
    if should_cancel_capacity(capacity_opp_1, type_):
        if not capacity_opp_2:
            return None, None
        capacity_opp_1 = None
        
    if should_cancel_capacity(capacity_opp_2, type_):
        if not capacity_opp_1:
            return None, None
        capacity_opp_2 = None
        
    capacity.types.remove(type_)
    if not capacity.types:
        return capacity_opp_1, capacity_opp_2
        
    return capacity_opp_1, capacity_opp_2

def apply_cancel_data_modif(capacity: Capacity, 
                          capacity_opp_1: Optional[Capacity], 
                          capacity_opp_2: Optional[Capacity]) -> Tuple[Optional[Capacity], Optional[Capacity]]:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types
    power/damage/attack/life/pillz.
    """
    if capacity.how != "cancel":
        return capacity_opp_1, capacity_opp_2
    
    # Traiter chaque type séquentiellement
    for type_ in TYPES_TO_CHECK:
        capacity_opp_1, capacity_opp_2 = process_type(capacity, capacity_opp_1, capacity_opp_2, type_)
        if capacity_opp_1 is None and capacity_opp_2 is None:
            return None, None
            
    return capacity_opp_1, capacity_opp_2


def apply_all_protect_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    if card1.ability_fight: (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.ability_fight, card2.ability_fight, card2.bonus_fight)
    if card1.bonus_fight: (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.bonus_fight, card2.ability_fight, card2.bonus_fight)
    if card2.ability_fight: (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.ability_fight, card1.ability_fight, card1.bonus_fight)
    if card2.bonus_fight: (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.bonus_fight, card1.ability_fight, card1.bonus_fight)


def apply_protect_enemy_data_modif(capacity_1: Capacity, capacity_opp_1: Capacity, capacity_opp_2: Capacity) -> Tuple[Capacity, Capacity]:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    # Liste des capacités avec l'attribut "how" qui ne doivent pas être protégées
    list_how_not_protect = ["cancel", "stop", "copy", "Protection"]

    if capacity_1.how == "Protection":
        if "power" in capacity_1.types:
            if capacity_opp_1 and "power" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                if not capacity_opp_2: return (None, None)
                capacity_opp_1 = None
            if capacity_opp_2 and "power" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                if not capacity_opp_1: return (None, None)
                capacity_opp_2 = None
            if capacity_opp_1 and all(x in capacity_opp_1.types for x in ["power", "damage"]) and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                if not capacity_opp_2: return (None, None)
                capacity_opp_1 = None
        if "damage" in capacity_1.types:
            if capacity_opp_1 and "damage" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                if not capacity_opp_2: return (None, None)
                capacity_opp_1 = None
            if capacity_opp_2 and "damage" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                if not capacity_opp_1: return (None, None)
                capacity_opp_2 = None
        elif "attack" in capacity_1.types:
            if capacity_opp_1 and "attack" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                if not capacity_opp_2: return (None, None)
                capacity_opp_1 = None
            if capacity_opp_2 and "attack" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                if not capacity_opp_1: return (None, None)
                capacity_opp_2 = None
                
    return capacity_opp_1, capacity_opp_2

def apply_exchange_or_copy_data(card1: Card, card2: Card, capacity: Capacity) -> Capacity:
    if "power" in capacity.types:
        if capacity.how == "exchange":
            card1.power_fight, card2.power_fight = card2.power, card1.power
            capacity = None
        elif capacity.how == "copy":
            card1.power_fight = card2.power
            capacity = None
    if "damage" in capacity.types:
        if capacity.how == "exchange":
            card1.damage_fight, card2.damage_fight = card2.damage, card1.damage
            capacity = None
        elif capacity.how == "copy":
            card1.damage_fight = card2.damage
            capacity = None
    return capacity

def apply_ability_stop_ability(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity ,Capacity]:
    """
    Applique une l'ability : "Stop Opp. Ability"
    """
    if bonus_2 and ((bonus_2.how == "Protection" and "ability" in bonus_2.types) or (bonus_2.how == "stop" and "ability" in bonus_2.types)):
        bonus_2 = None
        if bonus_1 and bonus_1.how == "stop" and "bonus" in bonus_1.types:
            bonus_1 = None
            if ability_2:
                if ability_2.condition_effect == "stop":
                    ability_2.condition_effect = ""
                else:
                    ability_2 = None
        elif ability_2 and ability_2.condition_effect == "stop":
            ability_2 = None
    elif ability_2: 
        if ability_2.condition_effect == "stop":
            ability_2.condition_effect = ""
        else:
            ability_2 = None
    return None, ability_2, bonus_1, bonus_2

def apply_bonus_stop_ability(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Ability"
    """
    if bonus_2 and ((bonus_2.how == "Protection" and "ability" in bonus_2.types) or (bonus_2.how == "stop" and "bonus" in bonus_2.types)):
        bonus_2 = None
        if ability_1 and ability_1.how == "stop" and "bonus" in ability_1.types:
            ability_1 = None
            if ability_2:
                if ability_2.condition_effect == "stop":
                    ability_2.condition_effect = ""
                else:
                    ability_2 = None
        elif ability_2 and ability_2.condition_effect == "stop":
            ability_2 = None
    elif ability_2:
        if ability_2.condition_effect == "stop":
            ability_2.condition_effect = ""
        else:
            ability_2 = None
    
    return None, ability_1, ability_2, bonus_2

def apply_ability_stop_bonus(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity ,Capacity]:
    """
    Applique une l'ability : "Stop Opp. Bonus"
    """
    if ability_2 and ((ability_2.how == "Protection" and "bonus" in ability_2.types) or (ability_2.how == "stop" and "ability" in ability_2.types)):
        ability_2 = None
        if bonus_1 and bonus_1.how == "stop" and "bonus" in bonus_1.types:
            bonus_1 = None
            if bonus_2:
                if bonus_2.condition_effect == "stop":
                    bonus_2.condition_effect = ""
                else:
                    bonus_2 = None
        elif bonus_2 and bonus_2.condition_effect == "stop":
            bonus_2 = None
    elif bonus_2:
        if bonus_2.condition_effect == "stop":
            bonus_2.condition_effect = ""
        else:
            bonus_2 = None
    
    return None, ability_2, bonus_1, bonus_2

def apply_bonus_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Bonus"
    """
    if ability_2 and ((ability_2.how == "Protection" and "bonus" in ability_2.types) or (ability_2.how == "stop" and "bonus" in ability_2.types)):
        ability_2 = None
        if ability_1 and ability_1.how == "stop" and "ability" in ability_1.types:
            ability_1 = None
            if bonus_2:
                if bonus_2.condition_effect == "stop":
                    bonus_2.condition_effect = ""
                else:
                    bonus_2 = None
        elif bonus_2 and bonus_2.condition_effect == "stop":
            bonus_2 = None
    elif bonus_2:
        if bonus_2.condition_effect == "stop":
            bonus_2.condition_effect = ""
        else:
            bonus_2 = None
    
    return None, ability_1, ability_2, bonus_2


def apply_ability_copy_ability(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Ability"
    """
    if ability_2:
        if ability_2.how == "copy" and "ability" in ability_2.types:
            return None, None, bonus_1, bonus_2

        if ability_2.how == "copy" and "bonus" in ability_2.types:
            if bonus_1:
                if bonus_1.how == "copy" and "ability" in bonus_1.types:
                    return None, None, None, bonus_2

                if bonus_1.how == "copy" and "bonus" in bonus_1.types:
                    if bonus_2 and bonus_2.how == "copy" and ("ability" in bonus_2.types or "bonus" in bonus_2.types):
                        return None, None, None, None
                    return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

            return copy.deepcopy(bonus_1), copy.deepcopy(bonus_1), bonus_1, bonus_2

    return copy.deepcopy(ability_2), ability_2, bonus_1, bonus_2

def apply_bonus_copy_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Bonus"
    """
    if bonus_2:
        if bonus_2.how == "copy" and "bonus" in bonus_2.types:
            return ability_1, ability_2, None, None

        if bonus_2.how == "copy" and "ability" in bonus_2.types:
            if ability_1:
                if ability_1.how == "copy" and "bonus" in ability_1.types:
                    return None, ability_2, None, None

                if ability_1.how == "copy" and "ability" in ability_1.types:
                    if ability_2 and ability_2.how == "copy" and ("ability" in ability_2.types or "bonus" in ability_2.types):
                        return None, None, None, None
                    return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

            return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, ability_2, copy.deepcopy(bonus_2), bonus_2

def apply_bonus_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Ability"
    """
    if ability_2:
        if ability_2.how == "copy" and "bonus" in ability_2.types:
            return ability_1, None, None, bonus_2

        if ability_2.how == "copy" and "ability" in ability_2.types:
            if ability_1:
                if ability_1.how == "copy" and "ability" in ability_1.types:
                    return None, None, None, bonus_2

                if ability_1.how == "copy" and "bonus" in ability_1.types:
                    if bonus_2 and bonus_2.how == "copy" and ("ability" in bonus_2.types or "bonus" in bonus_2.types):
                        return None, None, None, None
                    return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

            return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, copy.deepcopy(ability_2), bonus_1, bonus_2

def apply_ability_copy_bonus(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Bonus"
    """
    if bonus_2:
        if bonus_2.how == "copy" and "ability" in bonus_2.types:
            return copy.deepcopy(bonus_2), ability_2, None, None

        if bonus_2.how == "copy" and "bonus" in bonus_2.types:
            if bonus_1:
                if bonus_1.how == "copy" and "bonus" in bonus_1.types:
                    return None, ability_2, None, None

                if bonus_1.how == "copy" and "ability" in bonus_1.types:
                    if ability_2 and ability_2.how == "copy" and ("ability" in ability_2.types or "bonus" in ability_2.types):
                        return None, None, None, None
                    return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

            return copy.deepcopy(bonus_1), ability_2, copy.deepcopy(bonus_1), bonus_2

    return copy.deepcopy(bonus_2), ability_2, bonus_1, bonus_2