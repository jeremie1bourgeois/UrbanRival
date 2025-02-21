from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_3(game: Game, card1: Card, card2: Card) -> None:
    has_ally_won: bool = card1.win
    
    if card1.ability_fight: card1.ability_fight = check_capacity_condition_lvl_3(card1.ability_fight, has_ally_won)
    if card1.bonus_fight: card1.bonus_fight = check_capacity_condition_lvl_3(card1.bonus_fight, has_ally_won)
    if card2.ability_fight: card2.ability_fight = check_capacity_condition_lvl_3(card2.ability_fight, not has_ally_won)
    if card2.bonus_fight: card2.bonus_fight = check_capacity_condition_lvl_3(card2.bonus_fight, not has_ally_won)
    
    if card1.ability_fight: card1.ability_fight = apply_target_ally_effects(game, game.ally, game.enemy, card1.ability_fight, card1, card2)
    if card1.bonus_fight: card1.bonus_fight = apply_target_ally_effects(game, game.ally, game.enemy, card1.bonus_fight, card1, card2)
    if card2.ability_fight: card2.ability_fight = apply_target_enemy_effects(game, game.enemy, game.ally, card2.ability_fight, card2, card1)
    if card2.bonus_fight: card2.bonus_fight = apply_target_enemy_effects(game, game.enemy, game.ally, card2.bonus_fight, card2, card1)

    if card1.ability_fight: card1.ability_fight = apply_target_both_effects(game, game.ally, game.enemy, card1.ability_fight, card1, card2)
    if card1.bonus_fight: card1.bonus_fight = apply_target_both_effects(game, game.ally, game.enemy, card1.bonus_fight, card1, card2)
    if card2.ability_fight: card2.ability_fight = apply_target_both_effects(game, game.enemy, game.ally, card2.ability_fight, card2, card1)
    if card2.bonus_fight: card2.bonus_fight = apply_target_both_effects(game, game.enemy, game.ally, card2.bonus_fight, card2, card1)

    if card1.ability_fight: card1.ability_fight = apply_target_enemy_effects(game, game.ally, game.enemy, card1.ability_fight, card1, card2)
    if card1.bonus_fight: card1.bonus_fight = apply_target_enemy_effects(game, game.ally, game.enemy, card1.bonus_fight, card1, card2)
    if card2.ability_fight: card2.ability_fight = apply_target_enemy_effects(game, game.enemy, game.ally, card2.ability_fight, card2, card1)
    if card2.bonus_fight: card2.bonus_fight = apply_target_enemy_effects(game, game.enemy, game.ally, card2.bonus_fight, card2, card1)

def apply_reanimate(game: Game, player1: Player, player2: Player, card1: Card, card2: Card) -> None:
    if card1.ability_fight and "reanimate" in card1.ability_fight.types:
        card1.ability_fight = apply_target_ally_effects(game, player1, player2, card1.ability_fight, card1, card2)
    if card1.bonus_fight and "reanimate" in card1.bonus_fight.types:
        card1.bonus_fight = apply_target_ally_effects(game, player1, player2, card1.bonus_fight, card1, card2)
    if card2.ability_fight and "reanimate" in card2.ability_fight.types:
        card2.ability_fight = apply_target_ally_effects(game, player2, player1, card2.ability_fight, card2, card1)
    if card2.bonus_fight and "reanimate" in card2.bonus_fight.types:
        card2.bonus_fight = apply_target_ally_effects(game, player2, player1, card2.bonus_fight, card2, card1)

def check_capacity_condition_lvl_3(capacity: Capacity, has_won: bool) -> Capacity:
    if capacity.effect_conditions == []:
        return capacity if has_won else None
    elif "backlash" in capacity.effect_conditions:
        if has_won:
            capacity.target = "ally"
            capacity.effect_conditions = ""
            return capacity
        return None
    elif "defeat" in capacity.effect_conditions:
        if not has_won:
            capacity.effect_conditions = ""
            return capacity
        return None
    elif "victory_defeat" in capacity.effect_conditions:
        capacity.effect_conditions = ""
        return capacity
    else:
        raise ValueError(f"Invalid effect_conditions (check_capacity_condition_lvl_3): {capacity.effect_conditions}")


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

# Mapping des fonctions de bonus
_BONUS_FUNCS = {
    "": _bonus_empty,
    "growth": _bonus_growth,
    "degrowth": _bonus_degrowth,
    "support": _bonus_support,
    "equalizer": _bonus_equalizer,
    "brawl": _bonus_brawl,
    "nb_life_lost": _bonus_nb_life_lost,
    "nb_pillz_lost": _bonus_nb_pillz_lost,
    "nb_pillz_left": _bonus_nb_pillz_left,
    "nb_life_left": _bonus_nb_life_left
}

# Mapping des types de capacité aux attributs à modifier
_TYPE_MAP = {
    "life": "life",
    "pillz": "pillz",
    "reanimate": "life",
}

def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    # Vérifier si la capacité cible un allié
    if capacity.target != "ally":
        return capacity

    # Récupérer les attributs correspondants aux types de capacité
    attrs = [_TYPE_MAP.get(type_) for type_ in capacity.types if _TYPE_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne la capacité sans modification
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus correspondante
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_ally_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus en utilisant la fonction de bonus
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Appliquer le bonus aux attributs de la carte alliée
    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value = getattr(player1, attr)
                if current_value < capacity.borne:
                    setattr(player1, attr, min(capacity.borne, current_value + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value = getattr(player1, attr)
                if current_value > capacity.borne:
                    setattr(player1, attr, max(capacity.borne, current_value + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value = getattr(player1, attr)
            setattr(player1, attr, current_value + bonus)

    return capacity

def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    # Vérifier si la capacité cible un ennemi
    if capacity.target != "enemy":
        return capacity

    # Récupérer les attributs correspondants aux types de capacité
    attrs = [_TYPE_MAP.get(type_) for type_ in capacity.types if _TYPE_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne la capacité sans modification
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus correspondante
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_enemy_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus en utilisant la fonction de bonus
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Appliquer le bonus aux attributs de la carte ennemie
    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value = getattr(player2, attr)
                if current_value < capacity.borne:
                    setattr(player2, attr, min(capacity.borne, current_value + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value = getattr(player2, attr)
                if current_value > capacity.borne:
                    setattr(player2, attr, max(capacity.borne, current_value + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value = getattr(player2, attr)
            setattr(player2, attr, current_value + bonus)

    return capacity


def apply_target_both_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    # Vérifier si la capacité cible les deux cartes (alliée et ennemie)
    if capacity.target != "both":
        return capacity

    # Récupérer les attributs correspondants aux types de capacité
    attrs = [_TYPE_MAP.get(type_) for type_ in capacity.types if _TYPE_MAP.get(type_)]

    # Si aucun attribut n'est trouvé, on retourne la capacité sans modification
    if not attrs:
        return capacity

    # Récupérer la fonction de bonus correspondante
    bonus_func = _BONUS_FUNCS.get(capacity.how)
    if not bonus_func:
        raise ValueError(f"Invalid how (apply_target_both_effects): {capacity.how} for {capacity.types}")

    # Calculer le bonus en utilisant la fonction de bonus
    bonus = capacity.value * bonus_func(game, player1, player2, card1, card2)

    # Appliquer le bonus aux attributs des deux cartes (alliée et ennemie)
    if capacity.borne is not None and capacity.borne != -1:
        if capacity.value > 0:  # Augmentation avec borne max
            for attr in attrs:
                current_value1 = getattr(player1, attr)
                current_value2 = getattr(player2, attr)
                if current_value1 < capacity.borne:  # Vérification pour card1
                    setattr(player1, attr, min(capacity.borne, current_value1 + bonus))
                if current_value2 < capacity.borne:  # Vérification pour card2
                    setattr(player2, attr, min(capacity.borne, current_value2 + bonus))
        else:  # Diminution avec borne min
            for attr in attrs:
                current_value1 = getattr(player1, attr)
                current_value2 = getattr(player2, attr)
                if current_value1 > capacity.borne:  # Vérification pour card1
                    setattr(player1, attr, max(capacity.borne, current_value1 + bonus))
                if current_value2 > capacity.borne:  # Vérification pour card2
                    setattr(player2, attr, max(capacity.borne, current_value2 + bonus))
    else:  # Pas de borne
        for attr in attrs:
            current_value1 = getattr(card1, attr)
            current_value2 = getattr(card2, attr)
            setattr(player1, attr, current_value1 + bonus)
            setattr(player2, attr, current_value2 + bonus)

    return capacity
