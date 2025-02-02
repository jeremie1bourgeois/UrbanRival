from typing import Tuple
from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_2(game: Game, player1: Player, player2: Player, card1: Card, card2: Card) -> None:
    card1.ability = apply_target_ally_effects(game, player1, player2, card1.ability, card1, card2)
    card1.bonus = apply_target_ally_effects(game, player1, player2, card1.bonus, card1, card2)
    card2.ability = apply_target_ally_effects(game, player2, player1, card2.ability, card2, card1)
    card2.bonus = apply_target_ally_effects(game, player2, player1, card2.bonus, card2, card1)
    
    card1.ability = apply_target_enemy_effects(game, player1, player2, card1.ability, card1, card2)
    card1.bonus = apply_target_enemy_effects(game, player1, player2, card1.bonus, card1, card2)
    card2.ability = apply_target_enemy_effects(game, player2, player1, card2.ability, card2, card1)
    card2.bonus = apply_target_enemy_effects(game, player2, player1, card2.bonus, card2, card1)


# Fonctions de bonus définies en dehors
def _bonus_growth(game, player1, player2, card1, card2):
    return game.nb_turn

def _bonus_degrowth(game, player1, player2, card1, card2):
    return 5 - game.nb_turn

def _bonus_support(game, player1, player2, card1, card2):
    return sum(1 for c in player1.cards if c.faction == card1.faction)

def _bonus_equalizer(game, player1, player2, card1, card2):
    return card2.stars

def _bonus_brawl(game, player1, player2, card1, card2):
    return sum(1 for c in player2.cards if c.faction == card2.faction)

def _bonus_nb_life_lost(game, player1, player2, card1, card2):
    return 12 - player1.life # change le hardcode 12

def _bonus_nb_pillz_lost(game, player1, player2, card1, card2):
    return 12 - player1.pillz # change le hardcode 12

def _bonus_nb_pillz_left(game, player1, player2, card1, card2):
    return player1.pillz

def _bonus_nb_life_left(game, player1, player2, card1, card2):
    return player1.life

def _bonus_empty(game, player1, player2, card1, card2):
    return 1

# Mapping défini une seule fois
_BONUS_FUNCS = {
    "Growth": _bonus_growth,
    "Degrowth": _bonus_degrowth,
    "Support": _bonus_support,
    "Equalizer": _bonus_equalizer,
    "Brawl": _bonus_brawl,
    "nb_life_lost": _bonus_nb_life_lost,
    "nb_pillz_lost": _bonus_nb_pillz_lost,
    "nb_pillz_left": _bonus_nb_pillz_left,
    "nb_life_left": _bonus_nb_life_left,
    "": _bonus_empty
}

# Mapping des attributs aussi défini une seule fois
_ATTR_MAP = {
    "attack": ["attack"],
    "damage": ["damage_fight"],
    "power": ["power_fight"],
    "power_and_damage": ["power_fight", "damage_fight"]
}

def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "ally":
        return capacity

    attrs = _ATTR_MAP.get(capacity.type, [])  # Récupère les attributs associés
    if not attrs:
        return capacity

    bonus_func = _BONUS_FUNCS.get(capacity.how, _bonus_empty)  # Récupère la fonction de bonus
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    for attr in attrs:
        current_value = getattr(card1, attr, 0)  # Valeur actuelle

        if capacity.borne is not None and capacity.borne != -1:
            if capacity.value > 0:  # Augmentation avec borne max
                setattr(card1, attr, min(capacity.borne, current_value + bonus))
            else:  # Diminution avec borne min
                setattr(card1, attr, max(capacity.borne, current_value + bonus))
        else:  # Pas de borne
            setattr(card1, attr, current_value + bonus)

    return None


def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "enemy":
        return capacity

    attrs = _ATTR_MAP.get(capacity.type)
    if not attrs:
        return capacity

    # Récupération de la fonction de bonus
    bonus_func = _BONUS_FUNCS.get(capacity.how, _bonus_empty)
    if not bonus_func:
        raise ValueError(f"Invalid how: {capacity.how} for {capacity.type}")
    
    # Calcul du bonus
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Application des modifications
    for attr in attrs:
        current_value = getattr(card2, attr)
        
        if capacity.borne != -1:
            if capacity.value > 0:  # Valeur positive
                if current_value < capacity.borne:
                    setattr(card2, attr, min(capacity.borne, current_value + bonus))
            else:  # Valeur négative
                if current_value > capacity.borne:
                    setattr(card2, attr, max(capacity.borne, current_value + bonus))
        else:  # Pas de borne
            setattr(card2, attr, current_value + bonus)

    return None


def apply_target_both_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target != "both":
        return capacity

    attrs = _ATTR_MAP.get(capacity.type, [])  # S'assure que c'est une liste

    if not attrs:  # Vérification pour éviter un plantage
        return capacity

    # Récupération de la fonction de bonus
    bonus_func = _BONUS_FUNCS.get(capacity.how, _bonus_empty)

    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    for attr in attrs:
        current_value = getattr(card1, attr)
        current_value2 = getattr(card2, attr)

        # Gestion des bornes
        if capacity.borne is not None and capacity.borne != -1:
            if capacity.value > 0:  # Augmentation
                setattr(card1, attr, min(capacity.borne, current_value + bonus))
                setattr(card2, attr, min(capacity.borne, current_value2 + bonus))
            else:  # Diminution
                setattr(card1, attr, max(capacity.borne, current_value + bonus))
                setattr(card2, attr, max(capacity.borne, current_value2 + bonus))
        else:  # Pas de borne
            setattr(card1, attr, current_value + bonus)
            setattr(card2, attr, current_value2 + bonus)

    return None
