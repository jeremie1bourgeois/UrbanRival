from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game

MAX_LIFE = 12  # change le hardcode 12
MAX_PILLZ = 12  # change le hardcode 12

def apply_capacity_lvl_4(game: Game, player1: Player, player2: Player, card1: Card, card2: Card) -> None:
    card1.ability_fight = add_endgame_effects_lvl_1(player1, card1.ability_fight) if card1.ability_fight else None
    card1.bonus_fight = add_endgame_effects_lvl_1(player1, card1.bonus_fight) if card1.bonus_fight else None
    card2.ability_fight = add_endgame_effects_lvl_1(player2, card2.ability_fight) if card2.ability_fight else None
    card2.bonus_fight = add_endgame_effects_lvl_1(player2, card2.bonus_fight) if card2.bonus_fight else None
    
    apply_active_effects(game, player1, player2, card1, card2)
    apply_active_effects(game, player2, player1, card2, card1)
    
    card1.ability_fight = add_endgame_effects_lvl_2(player1, card1.ability_fight) if card1.ability_fight else None
    card1.bonus_fight = add_endgame_effects_lvl_2(player1, card1.bonus_fight) if card1.bonus_fight else None
    card2.ability_fight = add_endgame_effects_lvl_2(player2, card2.ability_fight) if card2.ability_fight else None
    card2.bonus_fight = add_endgame_effects_lvl_2(player2, card2.bonus_fight) if card2.bonus_fight else None



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
    return MAX_LIFE - player1.life

def _bonus_nb_pillz_lost(game, player1, player2, card1, card2):
    return MAX_PILLZ - player1.pillz

def _bonus_nb_pillz_left(game, player1, player2, card1, card2):
    return player1.pillz

def _bonus_nb_life_left(game, player1, player2, card1, card2):
    return player1.life

def _bonus_empty(game, player1, player2, card1, card2):
    return 1

# Mapping des fonctions de bonus
_CALCUL_FUNCS = {
    "": _bonus_empty,
    "Growth": _bonus_growth,
    "Degrowth": _bonus_degrowth,
    "Support": _bonus_support,
    "Equalizer": _bonus_equalizer,
    "Brawl": _bonus_brawl,
    "nb_life_lost": _bonus_nb_life_lost,
    "nb_pillz_lost": _bonus_nb_pillz_lost,
    "nb_pillz_left": _bonus_nb_pillz_left,
    "nb_life_left": _bonus_nb_life_left
}

def _apply_poison_or_toxine(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> None:
    calcul_func: function = _CALCUL_FUNCS[capacity.how]
    if not calcul_func:
        raise ValueError(f"Invalid how: {capacity.how} for {capacity.types}")
    
    effect_value = calcul_func(game, player1, player2, card1, card2)
    
    if capacity.borne != -1:
        if capacity.borne < player2.life:
            player2.life -= min(effect_value, capacity.borne)
    else:
        player2.life -= effect_value
        
def _apply_heal_or_regen(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> None:
    calcul_func: function = _CALCUL_FUNCS[capacity.how]
    if not calcul_func:
        raise ValueError(f"Invalid how: {capacity.how} for {capacity.types}")
    
    effect_value = calcul_func(game, player1, player2, card1, card2)
    
    if capacity.borne != -1:
        if capacity.borne < player1.life:
            player1.life = min(player1.life + effect_value, capacity.borne)
    else:
        player1.life += effect_value
    

def _apply_dope_or_repair(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> None:
    calcul_func: function = _CALCUL_FUNCS[capacity.how]
    if not calcul_func:
        raise ValueError(f"Invalid how: {capacity.how} for {capacity.types}")
    
    effect_value = calcul_func(game, player1, player2, card1, card2)
    
    if capacity.borne != -1:
        if capacity.borne < player1.pillz:
            player1.pillz = min(player1.pillz + effect_value, capacity.borne)
    else:
        player1.pillz += effect_value

_EFFECTS_FUNCS = {
    "poison": _apply_poison_or_toxine,
    "toxine": _apply_poison_or_toxine,

    "dope": _apply_dope_or_repair,
    "repair": _apply_dope_or_repair,

    "regen": _apply_heal_or_regen,
    "heal": _apply_heal_or_regen,
    
}

def add_endgame_effects_lvl_1(player: Player, capacity: Capacity) -> Capacity:
    if len(capacity.types) != 1:
        raise ValueError("Only one type is allowed for endgame effects.")
    nb = len(player.effect_list)
    capacity_type = capacity.types[0]
    if capacity_type == "toxine":
        for i in range (nb):
            if player.effect_list[i].types[0] in ["poison", "toxine"]:
                player.effect_list[i] = capacity
                return None
    elif capacity_type == "regen":
        for i in range (nb):
            if player.effect_list[i].types[0] in ["regen", "heal"]:
                player.effect_list[i] = capacity
                return None
    elif capacity_type == "repair":
        for i in range (nb):
            if player.effect_list[i].types[0] == "repair":
                player.effect_list[i] = capacity
                return None
    return capacity

def add_endgame_effects_lvl_2(player: Player, capacity: Capacity) -> Capacity:
    if len(capacity.types) != 1:
        raise ValueError("Only one type is allowed for endgame effects.")
    
    nb = len(player.effect_list)
    capacity_type = capacity.types[0]
    if capacity_type == "poison":
        for i in range (nb):
            if player.effect_list[i].types[0] in ["poison", "toxine"]:
                player.effect_list[i] = capacity
                return None
    elif capacity_type == "heal":
        for i in range (nb):
            if player.effect_list[i].types[0] in ["regen", "heal"]:
                player.effect_list[i] = capacity
                return None
    elif capacity_type == "dope":
        for i in range (nb):
            if player.effect_list[i].types[0] == "dope":
                player.effect_list[i] = capacity
                return None
    return capacity
    
def apply_active_effects(game: Game, player1: Player, player2: Player, card1: Card, card2: Card) -> None:
    for effect in player1.effect_list:
        _EFFECTS_FUNCS[effect.types[0]](game, player1, player2, effect, card1, card2)
    for effect in player2.effect_list:
        _EFFECTS_FUNCS[effect.types[0]](game, player2, player1, effect, card2, card1)
