from typing import Tuple
from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.game import Game


def apply_capacity_lvl_2(game: Game, player1_card_index: int, player2_card_index: int, card1: Card, card2: Card) -> None:
    card1.ability = apply_target_ally_effects(game, player1_card_index, player2_card_index, card1.ability, card1, card2)
    card1.bonus = apply_target_ally_effects(game, player1_card_index, player2_card_index, card1.bonus, card1, card2)
    card2.ability = apply_target_ally_effects(game, player2_card_index, player1_card_index, card2.ability, card2, card1)
    card2.bonus = apply_target_ally_effects(game, player2_card_index, player1_card_index, card2.bonus, card2, card1)
    
    card1.ability = apply_target_enemy_effects(game, player1_card_index, player2_card_index, card1.ability, card1, card2)
    card1.bonus = apply_target_enemy_effects(game, player1_card_index, player2_card_index, card1.bonus, card1, card2)
    card2.ability = apply_target_enemy_effects(game, player2_card_index, player1_card_index, card2.ability, card2, card1)
    card2.bonus = apply_target_enemy_effects(game, player2_card_index, player1_card_index, card2.bonus, card2, card1)


def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card):
    if capacity.target == "ally":
        if capacity.type == "power":
            if capacity.how == "Growth": # "Growth: Power +X"
                card1.power_fight += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: Power +X"
                card1.power_fight += (capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: Power +X"
                card1.power_fight += (capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: Power +X"
                card1.power_fight += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Power +X"
                card1.power_fight += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_left": # "+X Power Per Pillz Left Max. Y"
                if capacity.borne != -1:
                    if card1.power_fight < capacity.borne: # check if power is already at max
                        card1.power_fight = min(card1.power_fight + capacity.value * game.ally.pillz, capacity.borne)
                else:
                    card1.power_fight += (capacity.value * game.ally.pillz)
            elif capacity.how == "": # "+X Power"
                card1.power_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power")
            return None
        elif capacity.type == "damage":
            if capacity.how == "Growth": # "Growth: Damage +X"
                card1.damage_fight += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": 
                if capacity.borne != -1: # "Degrowth: Damage +X Max. Y"
                    if card1.damage_fight < capacity.borne: # check if damage is already at max
                        card1.damage_fight = min(capacity.value * (5 - game.nb_turn), capacity.borne)
                else: # "Degrowth: Damage +X"
                    card1.damage_fight += (capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: Damage +X"
                card1.damage_fight += (capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: Damage +X"
                card1.damage_fight += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Damage +X"
                card1.damage_fight += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            # elif capacity.how == "nb_pillz_left": # pas de pouvoir comme ça ?
            #     card1.damage_fight += min(capacity.value * game.ally.pillz, capacity.borne)
            elif capacity.how == "": # "Damage +X"
                card1.damage_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for damage")
            return None
        elif capacity.type == "attack":
            if capacity.how == "Growth": # "Growth: Attack +X"
                card1.attack += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: Attack +X"
                card1.attack += (capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: Attack +X"
                card1.attack += (capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: Attack +X"
                card1.attack += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Attack +X"
                card1.attack += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_left": # "+X Atk Per Pillz Left"
                card1.attack += (capacity.value * game.ally.pillz)
            elif capacity.how == "nb_opp_dam": # "+X Attack Per Opp. Damage"
                card1.attack += (capacity.value * card2.damage)
            elif capacity.how == "nb_opp_pow": # "+X Attack Per Opp. Damage"
                card1.attack += (capacity.value * card2.power)
            elif capacity.how == "nb_life_lost": # "+X Attack Per Life Lost"
                card1.attack += (capacity.value * (12 - game.ally.life)) # change le hardcode 12
            elif capacity.how == "nb_pillz_lost": # "+X Attack Per Pillz Lost"
                card1.attack += (capacity.value * (12 - game.ally.pillz)) # change le hardcode 12
            # pas de pouvoir comme ça ?
            # elif capacity.how == "nb_pow_opp": # "+X Atk Per Pow Opp" 
            #     card1.attack = card1.attack + capacity.value * card2.power_fight
            elif capacity.how == "": # "+X Attack"
                card1.attack += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for attack")
            return None
        elif capacity.type == "power_and_damage":
            if capacity.how == "Growth":
                if capacity.borne != -1: # "Growth: -X Power And Damage, Min Y"
                    if card1.power_fight > capacity.borne: # check if power is already at min
                        card1.power_fight = max(capacity.borne, card1.power_fight + capacity.value * game.nb_turn)
                    if card1.damage_fight > capacity.borne: # check if damage is already at min
                        card1.damage_fight = max(capacity.borne, card1.damage_fight + capacity.value * game.nb_turn)
                else: # "Growth : Power & Damage +X"
                    card1.power_fight += (capacity.value * game.nb_turn)
                    card1.damage_fight += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth":
                if capacity.borne != -1: # existe peut-être pas ? "Degrowth: -X Power And Damage, Min Y"
                    if card1.power_fight > capacity.borne: # check if power is already at min
                        card1.power_fight = max(capacity.borne, card1.power_fight - capacity.value * (5 - game.nb_turn))
                    if card1.damage_fight > capacity.borne: # check if damage is already at min
                        card1.damage_fight = max(capacity.borne, card1.damage_fight - capacity.value * (5 - game.nb_turn))
                else: # "Degrowth: Power & Damage +X"  
                    card1.power_fight += (capacity.value * (5 - game.nb_turn))
                    card1.damage_fight += (capacity.value * (5 - game.nb_turn))       
            elif capacity.how == "Support": # "Support: Power & Damage +X"
                same_faction_count = sum(1 for card in player1.cards if card.faction == card1.faction)
                card1.power_fight += (capacity.value * same_faction_count)
                card1.damage_fight += (capacity.value * same_faction_count)
            elif capacity.how == "Equalizer": # "Equalizer: Power And Damage +X"
                card1.power_fight += (capacity.value * card2.stars)
                card1.damage_fight += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Power And Damage + x"
                card1.power_fight += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
                card1.damage_fight += (capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            # pas de pouvoir comme ça ?
            # elif capacity.how == "nb_pillz_left": # "+X Power & Damage Per Pillz Left"
            #     card1.power_fight += (capacity.value * player1.pillz)
            #     card1.damage_fight += (capacity.value * player1.pillz)
            elif capacity.how == "":
                card1.power_fight += capacity.value
                card1.damage_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")
            return None
        else:
            return capacity


def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card):
    if capacity.target == "enemy":
        if capacity.type == "power":
            if capacity.how == "Growth": # "Growth: -X Opp Power, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: -X Opp Power, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: -X Opp Power, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * sum(1 for card in player1.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp Power, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * card1.stars)
            elif capacity.how == "Brawl": # "Brawl: -X Opp Power, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "nb_life_lost": # "-X Opp Power Per Life Lost, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * (12 - player1.life)) # change le hardcode 12
            elif capacity.how == "nb_pillz_lost":
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * (12 - player1.pillz)) # change le hardcode 12
            elif capacity.how == "": # "-X Opp Power, Min Y",
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power")
            return None
        elif capacity.type == "damage":
            if capacity.how == "Growth": # "Growth: -X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": # "Degrowth: -X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: -X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * sum(1 for card in player1.cards if card.faction == card1.faction))    
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * card1.stars)
            elif capacity.how == "Brawl": # "Brawl: -X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_lost": # "-X Opp Damage Per Pillz Lost, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * (12 - player1.pillz)) # change le hardcode 12
            elif capacity.how == "": # "-X Opp Damage, Min Y"
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for damage")
            return None
        elif capacity.type == "attack":
            if capacity.how == "Growth": # "Growth: -X Opp Attack, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * game.nb_turn)
            # pas de pouvoir comme ça ?
            # elif capacity.how == "Degrowth":
            #     card2.attack += capacity.value * (5 - game.nb_turn)
            elif capacity.how == "Support": # "Support: -X Opp Attack, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * sum(1 for card in player1.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp Attack, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * card1.stars)
            elif capacity.how == "Brawl": # "Brawl: -X Opp Attack, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * sum(1 for card in player2.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_left": # "-X Opp Att. Per Pillz Left, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * player1.pillz)
            elif capacity.how == "nb_life_left": # "-X Opp Att. Per Life Left, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value * player1.life)
            elif capacity.how == "": # "-X Opp Attack, Min Y"
                if card2.attack > capacity.borne:
                    card2.attack = max(capacity.borne, card2.attack + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for attack")
            return None
        elif capacity.type == "power_and_damage":
            if capacity.how == "Degrowth": # "Degrowth: -X Opp Pow. And Dam., Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight * (5 - game.nb_turn))
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage * (5 - game.nb_turn))
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp Pow. & Dam., Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value * card1.stars)
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value * card1.stars)
            elif capacity.how == "": # "-X Opp Power And Damage, Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = max(capacity.borne, card2.power_fight + capacity.value)
                if card2.damage_fight > capacity.borne:
                    card2.damage_fight = max(capacity.borne, card2.damage_fight + capacity.value)
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")
            return None
        else:
            return capacity

