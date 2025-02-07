from typing import Tuple
import copy
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_1(card1: Card, card2: Card):
    apply_copy(card1, card2)
    apply_stop(card1, card2)
    delete_capacity_protection(card1, card2)

    apply_all_cancel_data_modif(card1, card2)
    apply_all_protect_data_modif(card1, card2)
    
    apply_exchange_or_copy_data(card1, card2)
    apply_exchange_or_copy_data(card2, card1)


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
    if card1.ability_fight.how == "stop":
        if "ability" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.ability_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)

    if card1.bonus_fight.how == "stop":
        if "ability" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
        elif "bonus" in card1.bonus_fight.types:
            (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)
    
    if card2.ability_fight.how == "stop":
        if "ability" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_ability(card2.ability_fight, card2.bonus_fight, card1.bonus_fight)
        elif "bonus" in card2.ability_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)
    
    if card2.bonus_fight.how == "stop":
        if "ability" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight)
        elif "bonus" in card2.bonus_fight.types:
            (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)

def delete_capacity_protection(card1: Card, card2: Card) -> None:
    """
    Supprime les capacités qui protègent les autres capacités car les stop ont déjà été appliqués
    """
    capacity_types = ["ability", "bonus"]

    if card1.ability_fight.how == "Protection" and (any(x in card1.ability_fight.types for x in capacity_types)):
        card1.ability_fight = None
    if card1.bonus_fight.how == "Protection" and (any(x in card1.bonus_fight.types for x in capacity_types)):
        card1.bonus_fight = None
    if card2.ability_fight.how == "Protection" and (any(x in card2.ability_fight.types for x in capacity_types)):
        card2.ability_fight = None
    if card2.bonus_fight.how == "Protection" and (any(x in card2.bonus_fight.types for x in capacity_types)):
        card2.bonus_fight = None


def apply_all_cancel_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types power/damage/attack
    """
    (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card1.ability_fight, card2.ability_fight, card2.bonus_fight)
    (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card1.bonus_fight, card2.ability_fight, card2.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card2.ability_fight, card1.ability_fight, card1.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card2.bonus_fight, card1.ability_fight, card1.bonus_fight)

def apply_cancel_data_modif(capacity: Capacity, capacity_opp_1: Capacity, capacity_opp_2: Capacity) -> Tuple[Capacity, Capacity]:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types power/damage/attack
    """
    # Liste des capacités avec l'attribut "how" qui ne doivent pas être annulées
    list_how_not_cancel = ["cancel", "stop", "copy", "Protection"]
    if capacity.how == "cancel":
        if "power" in capacity.types:
            if "power" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if "power" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif "damage" in capacity.types:
            if "damage" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if "damage" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif "attack" in capacity.types:
            if "attack" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if "attack" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif all(x in capacity.types for x in ["power", "damage"]):
            if ("power" in capacity_opp_1.types or "damage" in capacity_opp_1.types or all(x in capacity_opp_1.types for x in ["power", "damage"])) and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if ("power" in capacity_opp_2.types or "damage" in capacity_opp_2.types or all(x in capacity_opp_2.types for x in ["power", "damage"])) and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif "life" in capacity.types:
            if "life" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if "life" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif "pillz" in capacity.types:
            if "pillz" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if "pillz" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif all(x in capacity.types for x in ["life", "pillz"]):
            if ("pillz" in capacity_opp_1.types or "life" in capacity_opp_1.types or all(x in capacity_opp_1.types for x in ["pillz", "life"])) and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if ("pillz" in capacity_opp_2.types or "life" in capacity_opp_2.types or all(x in capacity_opp_2.types for x in ["pillz", "life"])) and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
    return capacity_opp_1, capacity_opp_2


def apply_all_protect_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.ability_fight, card2.ability_fight, card2.bonus_fight)
    (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.bonus_fight, card2.ability_fight, card2.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.ability_fight, card1.ability_fight, card1.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.bonus_fight, card1.ability_fight, card1.bonus_fight)



def apply_protect_enemy_data_modif(capacity_1: Capacity, capacity_opp_1: Capacity, capacity_opp_2: Capacity) -> Tuple[Capacity, Capacity]:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    # Liste des capacités avec l'attribut "how" qui ne doivent pas être protégées
    list_how_not_protect = ["cancel", "stop", "copy", "Protection"]
    if capacity_1.how == "Protection":
        if "power" in capacity_1.types:
            if "power" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                capacity_opp_1 = None
            if "power" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                capacity_opp_2 = None
            if all(x in capacity_opp_1.types for x in ["power", "damage"]) and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                capacity_opp_1 = None
        elif "damage" in capacity_1.types:
            if "damage" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                capacity_opp_1 = None
            if "damage" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                capacity_opp_2 = None
        elif "attack" in capacity_1.types:
            if "attack" in capacity_opp_1.types and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                capacity_opp_1 = None
            if "attack" in capacity_opp_2.types and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                capacity_opp_2 = None
        elif all(x in capacity_1.types for x in ["power", "damage"]):
            if (any(x in capacity_opp_1.types for x in ["power", "damage"]) or all(x in capacity_opp_1.types for x in ["power", "damage"])) and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "enemy":
                capacity_opp_1 = None
            if (any(x in capacity_opp_2.types for x in ["power", "damage"]) or all(x in capacity_opp_2.types for x in ["power", "damage"])) and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "enemy":
                capacity_opp_2 = None
    return capacity_opp_1, capacity_opp_2

def apply_exchange_or_copy_data(card1: Card, card2: Card) -> None:
    if "power" in card1.ability_fight.types:
        if card1.ability_fight.how == "exchange":
            card1.power_fight, card2.power_fight = card2.power, card1.power
        elif card1.ability_fight.how == "copy":
            card1.power_fight = card2.power
    if "damage" in card1.ability_fight.types:
        if card1.ability_fight.how == "exchange":
            card1.damage_fight, card2.damage_fight = card2.damage, card1.damage
        elif card1.ability_fight.how == "copy":
            card1.damage_fight = card2.damage
    if all(x in card1.ability_fight.types for x in ["power", "damage"]):
        if card1.ability_fight.how == "exchange":
            card1.power_fight, card2.power_fight = card2.power, card1.power
            card1.damage_fight, card2.damage_fight = card2.damage, card1.damage
        elif card1.ability_fight.how == "copy":
            card1.power_fight = card2.power
            card1.damage_fight = card2.damage

def apply_ability_stop_ability(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity ,Capacity]:
    """
    Applique une l'ability : "Stop Opp. Ability"
    """
    if (bonus_2.how == "Protection" and "ability" in bonus_2.types) or (bonus_2.how == "stop" and "ability" in bonus_2.types):
        bonus_2 = None
        if bonus_1.how == "stop" and "bonus" in bonus_1.types:
            bonus_1 = None
            # capacity activé lorsqu'elle est stoppée
            if ability_2.condition_effect == "stop":
                ability_2.condition_effect = ""
            else:
                ability_2 = None
        elif ability_2.condition_effect == "stop":
            ability_2 = None
    elif ability_2.condition_effect == "stop":
        ability_2.condition_effect = ""
    else:
        ability_2 = None

    return None, ability_2, bonus_1, bonus_2

def apply_bonus_stop_ability(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Ability"
    """
    if (bonus_2.how == "Protection" and "ability" in bonus_2.types) or (bonus_2.how == "stop" and "bonus" in bonus_2.types):
        bonus_2 = None
        if ability_1.how == "stop" and "bonus" in ability_1.types:
            ability_1 = None
            # capacity activé lorsqu'elle est stoppée
            if ability_2.condition_effect == "stop":
                ability_2.condition_effect = ""
            else:
                ability_2 = None
        elif ability_2.condition_effect == "stop":
            ability_2 = None
    elif ability_2.condition_effect == "stop":
        ability_2.condition_effect = ""
    else:
        ability_2 = None
    
    return None, ability_1, ability_2, bonus_2

def apply_ability_stop_bonus(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity ,Capacity]:
    """
    Applique une l'ability : "Stop Opp. Bonus"
    """
    if (ability_2.how == "Protection" and "bonus" in ability_2.types) or (ability_2.how == "stop" and "ability" in ability_2.types):
        ability_2 = None
        if bonus_1.how == "stop" and "bonus" in bonus_1.types:
            bonus_1 = None
            # capacity activé lorsqu'elle est stoppée
            if bonus_2.condition_effect == "stop":
                bonus_2.condition_effect = ""
            else:
                bonus_2 = None
        elif bonus_2.condition_effect == "stop":
            bonus_2 = None
    elif bonus_2.condition_effect == "stop":
        bonus_2.condition_effect = ""
    else:
        bonus_2 = None
    
    return None, ability_2, bonus_1, bonus_2
def apply_bonus_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[None, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Bonus"
    """
    if (ability_2.how == "Protection" and "bonus" in ability_2.types) or (ability_2.how == "stop" and "bonus" in ability_2.types):
        ability_2 = None
        if ability_1.how == "stop" and "ability" in ability_1.types:
            ability_1 = None
            # capacity activé lorsqu'elle est stoppée
            if bonus_2.condition_effect == "stop":
                bonus_2.condition_effect = ""
            else:
                bonus_2 = None
        elif bonus_2.condition_effect == "stop":
            bonus_2 = None
    elif bonus_2.condition_effect == "stop":
        bonus_2.condition_effect = ""
    else:
        bonus_2 = None
    
    return None, ability_1, ability_2, bonus_2


def apply_ability_copy_ability(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Ability"
    """
    if ability_2.how == "copy" and "ability" in ability_2.types:
        return None, None, bonus_1, bonus_2

    if ability_2.how == "copy" and "bonus" in ability_2.types:
        if bonus_1.how == "copy" and "ability" in bonus_1.types:
            return None, None, None, bonus_2

        if bonus_1.how == "copy" and "bonus" in bonus_1.types:
            if bonus_2.how == "copy" and ("ability" in bonus_2.types or "bonus" in bonus_2.types):
                return None, None, None, None
            return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

        return copy.deepcopy(bonus_1), copy.deepcopy(bonus_1), bonus_1, bonus_2

    return copy.deepcopy(ability_2), ability_2, bonus_1, bonus_2

def apply_bonus_copy_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Bonus"
    """
    if bonus_2.how == "copy" and "bonus" in bonus_2.types:
        return ability_1, ability_2, None, None

    if bonus_2.how == "copy" and "ability" in bonus_2.types:
        if ability_1.how == "copy" and "bonus" in ability_1.types:
            return None, ability_2, None, None

        if ability_1.how == "copy" and "ability" in ability_1.types:
            if ability_2.how == "copy" and ("ability" in ability_2.types or "bonus" in ability_2.types):
                return None, None, None, None
            return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

        return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, ability_2, copy.deepcopy(bonus_2), bonus_2

def apply_bonus_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Ability"
    """
    if ability_2.how == "copy" and "bonus" in ability_2.types:
        return ability_1, None, None, bonus_2

    if ability_2.how == "copy" and "ability" in ability_2.types:
        if ability_1.how == "copy" and "ability" in ability_1.types:
            return None, None, None, bonus_2

        if ability_1.how == "copy" and "bonus" in ability_1.types:
            if bonus_2.how == "copy" and ("ability" in bonus_2.types or "bonus" in bonus_2.types):
                return None, None, None, None
            return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

        return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, copy.deepcopy(ability_2), bonus_1, bonus_2

def apply_ability_copy_bonus(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Bonus"
    """
    if bonus_2.how == "copy" and "ability" in bonus_2.types:
        return copy.deepcopy(bonus_2), ability_2, None, None

    if bonus_2.how == "copy" and "bonus" in bonus_2.types:
        if bonus_1.how == "copy" and "bonus" in bonus_1.types:
            return None, ability_2, None, None

        if bonus_1.how == "copy" and "ability" in bonus_1.types:
            if ability_2.how == "copy" and ("ability" in ability_2.types or "bonus" in ability_2.types):
                return None, None, None, None
            return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

        return copy.deepcopy(bonus_1), ability_2, copy.deepcopy(bonus_1), bonus_2

    return copy.deepcopy(bonus_2), ability_2, bonus_1, bonus_2