import math
from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_3(game: Game, card1: Card, card2: Card, has_ally_won: bool) -> None:
    card1.ability = apply_target_ally_effects(game, game.ally, game.enemy, card1.ability, card1, card2)
    card1.bonus = apply_target_ally_effects(game, game.ally, game.enemy, card1.bonus, card1, card2)
    card2.ability = apply_target_ally_effects(game, game.enemy, game.ally, card2.ability, card2, card1)
    card2.bonus = apply_target_ally_effects(game, game.enemy, game.ally, card2.bonus, card2, card1)
    
    card1.ability = apply_target_both_effects(game, game.ally, game.enemy, card1.ability, card1, card2)
    card1.bonus = apply_target_both_effects(game, game.ally, game.enemy, card1.bonus, card1, card2)
    card2.ability = apply_target_both_effects(game, game.enemy, game.ally, card2.ability, card2, card1)
    card2.bonus = apply_target_both_effects(game, game.enemy, game.ally, card2.bonus, card2, card1)
    
    card1.ability = apply_target_enemy_effects(game, game.ally, game.enemy, card1.ability, card1, card2)
    card1.bonus = apply_target_enemy_effects(game, game.ally, game.enemy, card1.bonus, card1, card2)
    card2.ability = apply_target_enemy_effects(game, game.enemy, game.ally, card2.ability, card2, card1)
    card2.bonus = apply_target_enemy_effects(game, game.enemy, game.ally, card2.bonus, card2, card1)

def check_capacity_condition(capacity: Capacity, has_won: bool) -> Capacity:
    if capacity.condition_effect == "":
        return capacity if has_won else None
    elif capacity.condition_effect == "Backlash":
        if has_won:
            capacity.target = "ally"
            capacity.condition_effect = ""
            return capacity
        return None
    elif capacity.condition_effect == "Defeat":
        if not has_won:
            capacity.condition_effect = ""
            return capacity
        return None
    elif capacity.condition_effect == "victory_defeat":
        capacity.condition_effect = ""
        return capacity
    else:
        raise ValueError(f"Invalid condition_effect: {capacity.condition_effect}")

def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    if capacity.target == "ally":
        if capacity.type == "life":
            if capacity.how == "Growth": # "Growth: +X Life"
                if capacity.value < 0:
                    if card1.life > capacity.borne:
                        card1.life = max(card1.life + capacity.value * game.nb_turn, capacity.borne)
                else:
                    card1.life += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: +X Life"
                card1.life += (capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: +X Life"
                card1.life += (capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: +X Life"
                card1.life += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: +X Life"
                card1.life += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "Damage": # "+X Life Per Damage Max. Y"
                if capacity.borne != -1:
                    if card1.life < capacity.borne:
                        card1.life = min(card1.life + capacity.value * card1.damage_fight, capacity.borne)
                else:
                    card1.life += (capacity.value * card1.damage_fight)
            elif capacity.how == "": # "+X Life Max. Y"
                if capacity.value > 0:
                    if capacity.borne != -1:
                        if card1.life < capacity.borne:
                            card1.life = min(card1.life + capacity.value, capacity.borne)
                    else:
                        card1.life += capacity.value
                else: # "Backlash: -X Life Min. Y"
                    if card1.life > capacity.borne:
                        card1.life = max(card1.life + capacity.value, capacity.borne)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for life")
            return None
        elif capacity.type == "pillz":
            if capacity.how == "":
                if capacity.value > 0: # "+X Pillz Max. Y":
                    if capacity.borne != -1:
                        if player1.pillz < capacity.borne:
                            player1.pillz = min(player1.pillz + capacity.value, capacity.borne)
                    else:
                        player1.pillz += capacity.value
                elif player1.pillz > capacity.borne: # "Backlash: -X Pillz Min Y"
                    player1.pillz = max(player1.pillz + capacity.value, capacity.borne)
            elif capacity.how == "Damage": # "+X Pillz Per Damage":
                player1.pillz += (capacity.value * card1.damage_fight)
            elif capacity.how == "Degrowth": # "Degrowth: +X Pillz"
                player1.pillz += (capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Growth": # "Growth: +X Pillz"
                player1.pillz += (capacity.value * game.nb_turn)
            elif capacity.how == "Support": # "Support: +X Pillz, Max. Y"
                if capacity.value != -1:
                    if player1.pillz < capacity.borne:
                        player1.pillz = min(player1.pillz + capacity.value, capacity.borne)
                else:
                    player1.pillz += capacity.value
            elif capacity.how == "Equalizer": # "Equalizer: +X Pillz"
                player1.pillz += (capacity.value * card2.stars)
            elif capacity.how == "Recover": # "Recover X Pillz Out Of Y"
                player1.pillz += max(1, math.floor(card1.pillz_fight * capacity.value / capacity.borne))
            else:
                raise ValueError(f"Invalid how: {capacity.how} for pillz")
            return None
        elif capacity.type == "pillz_life":
            if capacity.how == "": # "+X Pillz And Life"
                player1.pillz += capacity.value
                player1.life += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for pillz_life")
            return None
    return capacity

def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card):
    """
    Apply the capacity to the enemy player
    """
    if capacity.target == "enemy":
        if capacity.type == "life":
            if capacity.how == "": # "-X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value)
            elif capacity.how == "Growth": # "Growth: -X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: -X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: -X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value * sum(1 for card in player1.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value * card1.stars)
            elif capacity.how == "Brawl": # "Brawl: -X Opp. Life, Min Y"
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            else:
                raise ValueError(f"Invalid how: {capacity.how} for life")
            return None
        elif capacity.type == "pillz":
            if capacity.how == "": # "-X Opp Pillz. Min Y"
                if player2.pillz > capacity.borne:
                    player2.pillz = max(capacity.borne, player2.pillz + capacity.value)
            elif capacity.how == "Growth": # "Growth: -X Opp Pillz. Min Y"
                if player2.pillz > capacity.borne:
                    player2.pillz = max(capacity.borne, player2.pillz + capacity.value * game.nb_turn)
            elif capacity.how == "Brawl": # "Brawl: -X Opp. Pillz, Min Y"
                if player2.pillz > capacity.borne:
                    player2.pillz = max(capacity.borne, player2.pillz + capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            else:
                raise ValueError(f"Invalid how: {capacity.how} for pillz")
            return None
        elif capacity.type == "pillz_life":
            if capacity.how == "": # "-X Opp. Pillz And Life, Min Y"
                if player2.pillz > capacity.borne:
                    player2.pillz = max(capacity.borne, player2.pillz + capacity.value)
                if player2.life > capacity.borne:
                    player2.life = max(capacity.borne, player2.life + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for pillz_life")
            return None
    return capacity

def apply_target_both_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card):
    """
    Apply the capacity to both players
    """
    if capacity.target == "both":
        if capacity.type == "life":
            if capacity.how == "": # "+X Players Life"
                player1.life += capacity.value
                player2.life += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for life")
            return None
        elif capacity.type == "pillz":
            if capacity.how == "": # "-X Players Pillz. Min Y"
                if player1.pillz > capacity.borne:
                    player1.pillz = max(capacity.borne, player1.pillz + capacity.value)
                if player2.pillz > capacity.borne:
                    player2.pillz = max(capacity.borne, player2.pillz + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for pillz")
            return None
    return capacity