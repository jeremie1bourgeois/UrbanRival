import copy
from src.core.domain.round import Round
from src.core.domain.capacity import Capacity
from src.core.domain.player import Player
from src.core.domain.card import Card
from src.schemas.game_schemas import ProcessRoundInput
from src.core.domain.game import Game

from src.core.domain.game import Game

def process_round(game: Game, round_data: ProcessRoundInput) -> Game:
    try:
        # Vérifier les indices des cartes
        if not (0 <= round_data.player1_card_index < len(game.ally.cards)):
            raise ValueError(f"Invalid player1_card_index: {round_data.player1_card_index}")
        if not (0 <= round_data.player2_card_index < len(game.enemy.cards)):
            raise ValueError(f"Invalid player2_card_index: {round_data.player2_card_index}")

        # Vérifier le nombre de pillz
        if round_data.player1_pillz + 3 * round_data.player1_fury > game.ally.pillz:
            raise ValueError(f"Player 1 does not have enough pillz: {round_data.player1_pillz}")
        if round_data.player2_pillz + 3 * round_data.player2_fury > game.enemy.pillz:
            raise ValueError(f"Player 2 does not have enough pillz: {round_data.player2_pillz}")

        # Mise à jour des pillz
        game.ally.pillz -= round_data.player1_pillz + 3 * round_data.player1_fury
        game.enemy.pillz -= round_data.player2_pillz + 3 * round_data.player2_fury

        # Récupérer les cartes sélectionnées
        player1_card = game.ally.cards[round_data.player1_card_index]
        player2_card = game.enemy.cards[round_data.player2_card_index]

        # Initialiser les données de combat
        init_fight_data(player1_card, round_data.player1_pillz, round_data.player1_fury)
        init_fight_data(player2_card, round_data.player2_pillz, round_data.player2_fury)

        # Appliquer les effets de combat
        apply_combat_effects(game, player1_card, player2_card, player1_card.ability)
        apply_combat_effects(game, player1_card, player2_card, player1_card.bonus)
        apply_combat_effects(game, player2_card, player1_card, player2_card.ability)
        apply_combat_effects(game, player2_card, player1_card, player2_card.bonus)

        # Appliquer les fury
        if player1_card.fury:
            player1_card.damage_fight += 2
        if player2_card.fury:
            player2_card.damage_fight += 2

        # Calculer les attaques
        player1_attack = player1_card.power_fight * (round_data.player1_pillz + 1)
        player2_attack = player2_card.power_fight * (round_data.player2_pillz + 1)

        # Créer une nouvelle instance de Round
        round_result = Round()
        round_result.ally.card_index = round_data.player1_card_index  # Stocker l'index de la carte
        round_result.enemy.card_index = round_data.player2_card_index  # Stocker l'index de la carte

        # Résoudre le combat
        if player1_attack > player2_attack:
            game.enemy.life = max(0, game.enemy.life - player1_card.damage)
            round_result.ally.win = True
            round_result.enemy.win = False
        elif player2_attack > player1_attack:
            game.ally.life = max(0, game.ally.life - player2_card.damage)
            round_result.ally.win = False
            round_result.enemy.win = True
        elif game.turn:
            game.enemy.life = max(0, game.enemy.life - player1_card.damage)
            round_result.ally.win = True
            round_result.enemy.win = False
        else:
            game.ally.life = max(0, game.ally.life - player2_card.damage)
            round_result.ally.win = False
            round_result.enemy.win = True

        # Ajouter le round au history
        game.history.append(round_result)

        # Mettre à jour le tour
        player1_card.played = True
        player2_card.played = True

        game.nb_turn += 1
        game.turn = not game.turn

        return game
    except Exception as e:
        print(f"Exception in process_round: {e}")
        raise e
        

def check_capacity_condition(history, capacity: Capacity, player: Player):
    if capacity.condition_effect is None:
        return True
    elif capacity.condition_effect == "Revenge":
        return history[-1].ally.win == False
    elif capacity.condition_effect == "Reprisal":
        return history[-1] == 1
    elif capacity.condition_effect == "Confidence":
        return history[-1].ally.win == True
    else:
        True


def init_fight_data(card: Card, nb_pillz: int, fury: bool):
    card.power_fight = card.power
    card.damage_fight = card.damage
    card.ability_fight = copy.deepcopy(card.ability)
    card.bonus_fight = copy.deepcopy(card.bonus)
    card.pillz_fight = nb_pillz
    card.fury = fury
    card.attack = 0


def apply_combat_effects(game: Game, card1: Card, card2: Card, capacity: Capacity):
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
                card1.power_fight += (capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_left": # "+X Power Per Pillz Left Max. Y"
                if card1.power_fight < capacity.borne: # check if power is already at max
                    card1.power_fight = max(card1.power_fight + capacity.value * game.ally.pillz, capacity.borne)
            elif capacity.how == "": # "+X Power"
                card1.power_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power")
        elif capacity.type == "damage":
            if capacity.how == "Growth": # "Growth: Damage +X"
                card1.damage_fight += (capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth": 
                if capacity.borne is None: # "Degrowth: Damage +X"
                    card1.damage_fight += (capacity.value * (5 - game.nb_turn))
                else: # "Degrowth: Damage +X Max. Y"
                    if card1.damage_fight < capacity.borne: # check if damage is already at max
                        card1.damage_fight = max(capacity.value * (5 - game.nb_turn), capacity.borne)
            elif capacity.how == "Support": # "Support: Damage +X"
                card1.damage_fight += (capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction))
            elif capacity.how == "Equalizer": # "Equalizer: Damage +X"
                card1.damage_fight += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Damage +X"
                card1.damage_fight += (capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            # elif capacity.how == "nb_pillz_left": # pas de pouvoir comme ça ?
            #     card1.damage_fight += max(capacity.value * game.ally.pillz, capacity.borne)
            elif capacity.how == "": # "Damage +X"
                card1.damage_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for damage")
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
                card1.attack += (capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            elif capacity.how == "nb_pillz_left": # "+X Atk Per Pillz Left"
                card1.attack += (capacity.value * game.ally.pillz)
            elif capacity.how == "nb_opp_dam": # "+X Attack Per Opp. Damage"
                card1.attack += (capacity.value * card2.damage)
            elif capacity.how == "nb_opp_pow": # "+X Attack Per Opp. Damage"
                card1.attack += (capacity.value * card2.power)
            # pas de pouvoir comme ça ?
            # elif capacity.how == "nb_pow_opp": # "+X Atk Per Pow Opp" 
            #     card1.attack = card1.attack + capacity.value * card2.power_fight
            elif capacity.how == "": # "+X Attack"
                card1.attack += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for attack")
        elif capacity.type == "power_and_damage":
            if capacity.how == "Growth":
                if capacity.borne is None: # "Growth : Power & Damage +X"
                    card1.power_fight += (capacity.value * game.nb_turn)
                    card1.damage_fight += (capacity.value * game.nb_turn)
                else: # "Growth: -X Power And Damage, Min Y"
                    if card1.power_fight > capacity.borne: # check if power is already at min
                        card1.power_fight = min(capacity.borne, card1.power_fight - capacity.value * game.nb_turn)
                    if card1.damage_fight > capacity.borne: # check if damage is already at min
                        card1.damage_fight = min(capacity.borne, card1.damage_fight - capacity.value * game.nb_turn)
            elif capacity.how == "Degrowth":
                if capacity.borne is None: # "Degrowth: Power & Damage +X"
                    card1.power_fight += (capacity.value * (5 - game.nb_turn))
                    card1.damage_fight += (capacity.value * (5 - game.nb_turn))
                else: # existe peut-être pas ? "Degrowth: -X Power And Damage, Min Y"
                    if card1.power_fight > capacity.borne: # check if power is already at min
                        card1.power_fight = min(capacity.borne, card1.power_fight - capacity.value * (5 - game.nb_turn))
                    if card1.damage_fight > capacity.borne: # check if damage is already at min
                        card1.damage_fight = min(capacity.borne, card1.damage_fight - capacity.value * (5 - game.nb_turn))
            elif capacity.how == "Support": # "Support: Power & Damage +X"
                same_faction_count = sum(1 for card in game.ally.cards if card.faction == card1.faction)
                card1.power_fight += (capacity.value * same_faction_count)
                card1.damage_fight += (capacity.value * same_faction_count)
            elif capacity.how == "Equalizer": # "Equalizer: Power And Damage +X"
                card1.power_fight += (capacity.value * card2.stars)
                card1.damage_fight += (capacity.value * card2.stars)
            elif capacity.how == "Brawl": # "Brawl: Power And Damage + x"
                card1.power_fight += (capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
                card1.damage_fight += (capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            # pas de pouvoir comme ça ?
            # elif capacity.how == "nb_pillz_left": # "+X Power & Damage Per Pillz Left"
            #     card1.power_fight += (capacity.value * game.ally.pillz)
            #     card1.damage_fight += (capacity.value * game.ally.pillz)
            elif capacity.how == "":
                card1.power_fight += capacity.value
                card1.damage_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")
    elif capacity.target == "enemy":
        if capacity.type == "power":
            if capacity.how == "Growth":
                card2.power_fight = min(capacity.borne, card2.power_fight * game.nb_turn)
            elif capacity.how == "Degrowth":
                card2.power_fight = min(capacity.borne, card2.power_fight * (5 - game.nb_turn))
            elif capacity.how == "Support":
                card2.power_fight = min(capacity.borne, card2.power_fight + capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            elif capacity.how == "Equalizer":
                card2.power_fight = min(capacity.borne, card2.power_fight + capacity.value * card1.stars)
            elif capacity.how == "nb_pillz_left":
                card2.power_fight += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.power_fight += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power")
        elif capacity.type == "damage":
            if capacity.how == "Growth":
                card2.damage = min(capacity.borne, card2.damage * game.nb_turn)
            elif capacity.how == "Degrowth":
                card2.damage = min(capacity.borne, card2.damage * (5 - game.nb_turn))
            elif capacity.how == "Support":
                card2.damage = min(capacity.borne, card2.damage + capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            elif capacity.how == "Equalizer":
                card2.damage = min(capacity.borne, card2.damage + capacity.value * card1.stars)
            elif capacity.how == "nb_pillz_left":
                card2.damage += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.damage += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for damage")
        elif capacity.type == "attack":
            if capacity.how == "Growth":
                card2.attack += capacity.value * game.nb_turn
            elif capacity.how == "Degrowth":
                card2.attack += capacity.value * (5 - game.nb_turn)
            elif capacity.how == "Support":
                card2.attack += capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction)
            elif capacity.how == "Equalizer":
                card2.attack += capacity.value * card1.stars
            elif capacity.how == "nb_pillz_left":
                card2.attack += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.attack += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for attack")
        elif capacity.type == "power_and_damage":
            if capacity.how == "Growth":
                card2.power_fight = min(capacity.borne, card2.power_fight * game.nb_turn)
                card2.damage = min(capacity.borne, card2.damage * game.nb_turn)
            elif capacity.how == "Degrowth":
                card2.power_fight = min(capacity.borne, card2.power_fight * (5 - game.nb_turn))
                card2.damage = min(capacity.borne, card2.damage * (5 - game.nb_turn))
            elif capacity.how == "Support":
                same_faction_count = sum(1 for card in game.enemy.cards if card.faction == card2.faction)
                card2.power_fight = min(capacity.borne, card2.power_fight + capacity.value * same_faction_count)
                card2.damage = min(capacity.borne, card2.damage + capacity.value * same_faction_count)
            elif capacity.how == "Equalizer": # "Equalizer: -X Opp Pow. & Dam., Min Y"
                if card2.power_fight > capacity.borne:
                    card2.power_fight = min(capacity.borne, card2.power_fight - capacity.value * card1.stars)
                if card2.damage > capacity.borne:
                    card2.damage = min(capacity.borne, card2.damage - capacity.value * card1.stars)
            elif capacity.how == "nb_pillz_left":
                card2.power_fight += capacity.value * game.enemy.pillz
                card2.damage += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.power_fight += capacity.value
                card2.damage += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")


def check_round_correct(game: Game, round_data: ProcessRoundInput):
    if round_data.player1_card_index >= 4:
        raise ValueError("Player 1: invalid card index.")
    if round_data.player2_card_index >= 4:
        raise ValueError("Player 2: invalid card index.")
    if round_data.player1_pillz + 3 * round_data.player1_fury > game.ally.pillz:
        raise ValueError("Player 1: too many pillz.")
    if round_data.player2_pillz + 3 * round_data.player2_fury > game.enemy.pillz:
        raise ValueError("Player 2: too many pillz.")
    if game.ally.cards[round_data.player1_card_index].played:
        raise ValueError("Player 1: card already played.")
    if game.enemy.cards[round_data.player2_card_index].played:
        raise ValueError("Player 2: card already played.")


# def apply_end_capacity_effects(game: Game, card1: Card, card2: Card, capacity: Capacity):
#     if capacity.target == "ally":
        