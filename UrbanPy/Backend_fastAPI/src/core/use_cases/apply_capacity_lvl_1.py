from typing import Tuple
import copy
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_1(game: Game, card1: Card, card2: Card):
    apply_copy(card1, card2)
    apply_stop(card1, card2)
    delete_capacity_protection(card1, card2)

    apply_all_cancel_data_modif(card1, card2)
    apply_all_protect_data_modif(card1, card2)
    
    apply_exchange_or_copy_data(card1, card2)
    apply_exchange_or_copy_data(card2, card1)


def apply_copy(card1: Card, card2: Card):
    if card1.ability_fight.how == "copy" and card1.ability_fight.type == "ability":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_copy_ability(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
    elif card1.ability_fight.how == "copy" and card1.ability_fight.type == "bonus":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_copy_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)

    if card1.bonus_fight.how == "copy" and card1.bonus_fight.type == "ability":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_copy_ability(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
    elif card1.bonus_fight.how == "copy" and card1.bonus_fight.type == "bonus":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_copy_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight, card2.bonus_fight)
    
    if card2.ability_fight.how == "copy" and card2.ability_fight.type == "ability":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_copy_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
    elif card2.ability_fight.how == "copy" and card2.ability_fight.type == "bonus":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_copy_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
    
    if card2.bonus_fight.how == "copy" and card2.bonus_fight.type == "ability":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_copy_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
    elif card2.bonus_fight.how == "copy" and card2.bonus_fight.type == "bonus":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_copy_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight, card1.bonus_fight)
    
def apply_stop(card1: Card, card2: Card):
    if card1.ability_fight.how == "stop" and card1.ability_fight.type == "ability":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
    elif card1.ability_fight.how == "stop" and card1.ability_fight.type == "bonus":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_ability_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)

    if card1.bonus_fight.how == "stop" and card1.bonus_fight.type == "ability":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_ability(card1.ability_fight, card1.bonus_fight, card2.bonus_fight)
    elif card1.bonus_fight.how == "stop" and card1.bonus_fight.type == "bonus":
        (card1.ability_fight, card1.bonus_fight, card2.ability_fight, card2.bonus_fight) = apply_bonus_stop_bonus(card1.ability_fight, card2.ability_fight, card1.bonus_fight)
    
    if card2.ability_fight.how == "stop" and card2.ability_fight.type == "ability":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_ability(card2.ability_fight, card2.bonus_fight, card1.bonus_fight)
    elif card2.ability_fight.how == "stop" and card2.ability_fight.type == "bonus":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_ability_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)
    
    if card2.bonus_fight.how == "stop" and card2.bonus_fight.type == "ability":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_ability(card2.ability_fight, card1.ability_fight, card2.bonus_fight)
    elif card2.bonus_fight.how == "stop" and card2.bonus_fight.type == "bonus":
        (card2.ability_fight, card2.bonus_fight, card1.ability_fight, card1.bonus_fight) = apply_bonus_stop_bonus(card2.ability_fight, card1.ability_fight, card2.bonus_fight)

def delete_capacity_protection(card1: Card, card2: Card) -> None:
    """
    Supprime les capacités qui protègent les autres capacités car les stop ont déjà été appliqués
    """
    if card1.ability_fight.how == "Protection" and (card1.ability_fight.type == "ability" or card1.ability_fight.type == "bonus"):
        card1.ability_fight = None
    if card1.bonus_fight.how == "Protection" and (card1.bonus_fight.type == "ability" or card1.bonus_fight.type == "bonus"):
        card1.bonus_fight = None
    if card2.ability_fight.how == "Protection" and (card2.ability_fight.type == "ability" or card2.ability_fight.type == "bonus"):
        card2.ability_fight = None
    if card2.bonus_fight.how == "Protection" and (card2.bonus_fight.type == "ability" or card2.bonus_fight.type == "bonus"):
        card2.bonus_fight = None


def apply_all_cancel_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types power/damage/attack
    """
    (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card1.ability_fight, card1.bonus_fight, card2.ability_fight)
    (card2.ability_fight, card2.bonus_fight) = apply_cancel_data_modif(card1.bonus_fight, card1.ability_fight, card2.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card2.ability_fight, card2.bonus_fight, card1.ability_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_cancel_data_modif(card2.bonus_fight, card2.ability_fight, card1.bonus_fight)

def apply_cancel_data_modif(capacity: Capacity, capacity_opp_1: Capacity, capacity_opp_2: Capacity) -> Tuple[Capacity, Capacity]:
    """
    Applique les capacités qui annulent les modifications des autres capacités sur les types power/damage/attack
    """
    # Liste des capacités avec l'attribut "how" qui ne doivent pas être annulées
    list_how_not_cancel = ["cancel", "stop", "copy", "Protection"]
    if capacity.how == "cancel":
        if capacity.type == "power":
            if capacity_opp_1.type == "power" and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if capacity_opp_2.type == "power" and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "damage":
            if capacity_opp_1.type == "damage" and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if capacity_opp_2.type == "damage" and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "attack":
            if capacity_opp_1.type == "attack" and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if capacity_opp_2.type == "attack" and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "power_damage":
            if (capacity_opp_1.type == "power" or capacity_opp_1.type == "damage" or capacity_opp_1.type == "power_damage") and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if (capacity_opp_2.type == "power" or capacity_opp_2.type == "damage" or capacity_opp_2.type == "power_damage") and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "life":
            if capacity_opp_1.type == "life" and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if capacity_opp_2.type == "life" and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "pillz":
            if capacity_opp_1.type == "pillz" and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if capacity_opp_2.type == "pillz" and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
        elif capacity.type == "pillz_life":
            if (capacity_opp_1.type == "pillz" or capacity_opp_1.type == "life" or capacity_opp_1.type == "pillz_life") and capacity_opp_1.how not in list_how_not_cancel:
                capacity_opp_1 = None
            if (capacity_opp_2.type == "pillz" or capacity_opp_2.type == "life" or capacity_opp_2.type == "pillz_life") and capacity_opp_2.how not in list_how_not_cancel:
                capacity_opp_2 = None
    return capacity_opp_1, capacity_opp_2


def apply_all_protect_data_modif(card1: Card, card2: Card) -> None:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.ability_fight, card1.bonus_fight, card2.ability_fight)
    (card2.ability_fight, card2.bonus_fight) = apply_protect_enemy_data_modif(card1.bonus_fight, card1.ability_fight, card2.bonus_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.ability_fight, card2.bonus_fight, card1.ability_fight)
    (card1.ability_fight, card1.bonus_fight) = apply_protect_enemy_data_modif(card2.bonus_fight, card2.ability_fight, card1.bonus_fight)



def apply_protect_enemy_data_modif(capacity_1: Capacity, capacity_2: Capacity, capacity_opp_1: Capacity, capacity_opp_2: Capacity) -> Tuple[Capacity, Capacity]:
    """
    Applique les capacités qui protègent contre les capacités qui modifient les données de type power/damage/attack
    """
    # Liste des capacités avec l'attribut "how" qui ne doivent pas être protégées
    list_how_not_protect = ["cancel", "stop", "copy", "Protection"]
    if capacity_1.how == "Protection":
        if capacity_1.type == "power":
            if capacity_opp_1.type == "power" and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "ennemy":
                capacity_opp_1 = None
            if capacity_opp_2.type == "power" and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "ennemy":
                capacity_opp_2 = None
            if capacity_opp_1.type == "power_damage" and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "ennemy":
                capacity_opp_1 = None
        elif capacity_1.type == "damage":
            if capacity_opp_1.type == "damage" and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "ennemy":
                capacity_opp_1 = None
            if capacity_opp_2.type == "damage" and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "ennemy":
                capacity_opp_2 = None
        elif capacity_1.type == "attack":
            if capacity_opp_1.type == "attack" and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "ennemy":
                capacity_opp_1 = None
            if capacity_opp_2.type == "attack" and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "ennemy":
                capacity_opp_2 = None
        elif capacity_1.type == "power_damage":
            if (capacity_opp_1.type == "power" or capacity_opp_1.type == "damage" or capacity_opp_1.type == "power_damage") and capacity_opp_1.how not in list_how_not_protect and capacity_opp_1.target == "ennemy":
                capacity_opp_1 = None
            if (capacity_opp_2.type == "power" or capacity_opp_2.type == "damage" or capacity_opp_2.type == "power_damage") and capacity_opp_2.how not in list_how_not_protect and capacity_opp_2.target == "ennemy":
                capacity_opp_2 = None
    return capacity_opp_1, capacity_opp_2

def apply_exchange_or_copy_data(card1: Card, card2: Card) -> None:
    if card1.ability_fight.type == "power":
        if card1.ability_fight.how == "exchange":
            card1.power_fight = card2.power
            card2.power_fight = card1.power
        elif card1.ability_fight.how == "copy":
            card1.power_fight = card2.power
    if card1.ability_fight.type == "damage":
        if card1.ability_fight.how == "exchange":
            card1.damage_fight = card2.damage
            card2.damage_fight = card1.damage
        elif card1.ability_fight.how == "copy":
            card1.damage_fight = card2.damage
    if card1.ability_fight.type == "power_damage":
        if card1.ability_fight.how == "exchange":
            card1.power_fight = card2.power
            card1.damage_fight = card2.damage
            card2.power_fight = card1.power
            card2.damage_fight = card1.damage
        elif card1.ability_fight.how == "copy":
            card1.power_fight = card2.power
            card1.damage_fight = card2.damage


def apply_ability_stop_ability(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity]:
    """
    Applique une l'ability : "Stop Opp. Ability"
    """
    if (bonus_2.how == "Protection" and bonus_2.type == "ability") or (bonus_2.how == "stop" and bonus_2.type == "ability"):
        bonus_2 = None
        if bonus_1.how == "stop" and bonus_1.type == "bonus":
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

    return ability_2, bonus_1, bonus_2

def apply_bonus_stop_ability(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Ability"
    """
    if (bonus_2.how == "Protection" and bonus_2.type == "ability") or (bonus_2.how == "stop" and bonus_2.type == "bonus"):
        bonus_2 = None
        if ability_1.how == "stop" and ability_1.type == "bonus":
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
    
    return ability_1, ability_2, bonus_2

def apply_ability_stop_bonus(ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity]:
    """
    Applique une l'ability : "Stop Opp. Bonus"
    """
    if (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "ability"):
        ability_2 = None
        if bonus_1.how == "stop" and bonus_1.type == "bonus":
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
    
    return ability_2, bonus_1, bonus_2

def apply_bonus_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Stop Opp. Bonus"
    """
    if (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "bonus"):
        ability_2 = None
        if ability_1.how == "stop" and ability_1.type == "ability":
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
    
    return ability_1, ability_2, bonus_2


def apply_ability_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Ability"
    """
    if ability_2.how == "copy" and ability_2.type == "ability":
        return None, None, bonus_1, bonus_2

    if ability_2.how == "copy" and ability_2.type == "bonus":
        if bonus_1.how == "copy" and bonus_1.type == "ability":
            return None, None, None, bonus_2

        if bonus_1.how == "copy" and bonus_1.type == "bonus":
            if bonus_2.how == "copy" and (bonus_2.type == "ability" or bonus_2.type == "bonus"):
                return None, None, None, None
            return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

        return copy.deepcopy(bonus_1), copy.deepcopy(bonus_1), bonus_1, bonus_2

    return copy.deepcopy(ability_2), ability_2, bonus_1, bonus_2

def apply_bonus_copy_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Bonus"
    """
    if bonus_2.how == "copy" and bonus_2.type == "bonus":
        return ability_1, ability_2, None, None

    if bonus_2.how == "copy" and bonus_2.type == "ability":
        if ability_1.how == "copy" and ability_1.type == "bonus":
            return None, ability_2, None, None

        if ability_1.how == "copy" and ability_1.type == "ability":
            if ability_2.how == "copy" and (ability_2.type == "ability" or ability_2.type == "bonus"):
                return None, None, None, None
            return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

        return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, ability_2, copy.deepcopy(bonus_2), bonus_2

def apply_bonus_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique le bonus : "Copy Opp. Ability"
    """
    if ability_2.how == "copy" and ability_2.type == "bonus":
        return ability_1, None, None, bonus_2

    if ability_2.how == "copy" and ability_2.type == "ability":
        if ability_1.how == "copy" and ability_1.type == "ability":
            return None, None, None, bonus_2

        if ability_1.how == "copy" and ability_1.type == "bonus":
            if bonus_2.how == "copy" and (bonus_2.type == "ability" or bonus_2.type == "bonus"):
                return None, None, None, None
            return copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), copy.deepcopy(bonus_2), bonus_2

        return copy.deepcopy(ability_1), copy.deepcopy(ability_1), bonus_1, bonus_2

    return ability_1, copy.deepcopy(ability_2), bonus_1, bonus_2

def apply_ability_copy_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity) -> Tuple[Capacity, Capacity, Capacity, Capacity]:
    """
    Applique l'ability : "Copy Opp. Bonus"
    """
    if bonus_2.how == "copy" and bonus_2.type == "ability":
        return copy.deepcopy(bonus_2), ability_2, None, None

    if bonus_2.how == "copy" and bonus_2.type == "bonus":
        if bonus_1.how == "copy" and bonus_1.type == "bonus":
            return None, ability_2, None, None

        if bonus_1.how == "copy" and bonus_1.type == "ability":
            if ability_2.how == "copy" and (ability_2.type == "ability" or ability_2.type == "bonus"):
                return None, None, None, None
            return copy.deepcopy(ability_2), copy.deepcopy(ability_2), copy.deepcopy(ability_2), bonus_2

        return copy.deepcopy(bonus_1), ability_2, copy.deepcopy(bonus_1), bonus_2

    return copy.deepcopy(bonus_2), ability_2, bonus_1, bonus_2