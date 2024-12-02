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
        if round_data.player1_pillz > game.ally.pillz:
            raise ValueError(f"Player 1 does not have enough pillz: {round_data.player1_pillz}")
        if round_data.player2_pillz > game.enemy.pillz:
            raise ValueError(f"Player 2 does not have enough pillz: {round_data.player2_pillz}")

        game.ally.pillz = min(0, game.ally.pillz - round_data.player1_pillz)
        game.enemy.pillz = min(0, game.enemy.pillz - round_data.player2_pillz)

        # Récupérer les cartes sélectionnées
        player1_card = game.ally.cards[round_data.player1_card_index]
        player2_card = game.enemy.cards[round_data.player2_card_index]
        
        init_fight_data(player1_card, round_data.player1_pillz)
        init_fight_data(player2_card, round_data.player2_pillz)
        
        apply_combat_effects(game, player1_card, player2_card, player1_card.ability)
        apply_combat_effects(game, player1_card, player2_card, player1_card.bonus)
        
        apply_combat_effects(game, player2_card, player1_card, player2_card.ability)
        apply_combat_effects(game, player2_card, player1_card, player2_card.bonus)

        # Calculer les attaques
        player1_attack = player1_card.power * (round_data.player1_pillz + 1)
        player2_attack = player2_card.power * (round_data.player2_pillz + 1)

        # Résoudre le combat
        if player1_attack > player2_attack:
            game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        elif player2_attack > player1_attack:
            game.ally.life = max(0, game.ally.life - player2_card.damage)
        elif game.turn:
            game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        else:
            game.ally.life = max(0, game.ally.life - player2_card.damage)

        # Mettre à jour le tour
        game.nb_turn += 1
        game.ally.pillz += 1
        game.enemy.pillz += 1
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
    

def init_fight_data(card: Card, nb_pillz: int):
    card.power_fight = card.power
    card.damage_fight = card.damage
    card.ability_fight = card.ability
    card.bonus_fight = card.bonus
    card.pillz_fight = nb_pillz
    card.attack = 0


def apply_combat_effects(game: Game, card1: Card, card2: Card, capacity: Capacity):
    if capacity.target == "ally":
        if capacity.type == "power":
            if capacity.how == "Growth":
                card1.power = card1.power * game.nb_turn
            elif capacity.how == "Degrowth":
                card1.power = card1.power * (5 - game.nb_turn)
            elif capacity.how == "Support":
                card1.power = card1.power + capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction)
            elif capacity.how == "Equalizer":
                card1.power = card1.power + capacity.value * card2.stars
            elif capacity.how == "nb_pillz_left":
                card1.power += capacity.value * game.ally.pillz
            elif capacity.how == "":
                card1.power += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power")
        elif capacity.type == "damage":
            if capacity.how == "Growth":
                card1.damage = card1.damage * game.nb_turn
            elif capacity.how == "Degrowth":
                card1.damage = card1.damage * (5 - game.nb_turn)
            elif capacity.how == "Support":
                card1.damage = card1.damage + capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction)
            elif capacity.how == "Equalizer":
                card1.damage = card1.damage + capacity.value * card2.stars
            elif capacity.how == "nb_pillz_left":
                card1.damage += capacity.value * game.ally.pillz
            elif capacity.how == "":
                card1.damage += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for damage")
        elif capacity.type == "attack":
            if capacity.how == "Growth":
                card1.attack += capacity.value * game.nb_turn
            elif capacity.how == "Degrowth":
                card1.attack += capacity.value * (5 - game.nb_turn)
            elif capacity.how == "Support":
                card1.attack += capacity.value * sum(1 for card in game.ally.cards if card.faction == card1.faction)
            elif capacity.how == "Equalizer":
                card1.attack += capacity.value * card2.stars
            elif capacity.how == "nb_pillz_left":
                card1.attack += capacity.value * game.ally.pillz
            elif capacity.how == "nb_dam_opp_left":
                card1.attack = card1.attack + capacity.value * card2.damage
            elif capacity.how == "":
                card1.attack += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for attack")
        elif capacity.type == "power_and_damage":
            if capacity.how == "Growth":
                card1.power = card1.power * game.nb_turn
                card1.damage = card1.damage * game.nb_turn
            elif capacity.how == "Degrowth":
                card1.power = card1.power * (5 - game.nb_turn)
                card1.damage = card1.damage * (5 - game.nb_turn)
            elif capacity.how == "Support":
                same_faction_count = sum(1 for card in game.ally.cards if card.faction == card1.faction)
                card1.power = card1.power + capacity.value * same_faction_count
                card1.damage = card1.damage + capacity.value * same_faction_count
            elif capacity.how == "Equalizer":
                card1.power = card1.power + capacity.value * card2.stars
                card1.damage = card1.damage + capacity.value * card2.stars
            elif capacity.how == "nb_pillz_left":
                card1.power += capacity.value * game.ally.pillz
                card1.damage += capacity.value * game.ally.pillz
            elif capacity.how == "":
                card1.power += capacity.value
                card1.damage += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")
    elif capacity.target == "enemy":
        if capacity.type == "power":
            if capacity.how == "Growth":
                card2.power = min(capacity.borne, card2.power * game.nb_turn)
            elif capacity.how == "Degrowth":
                card2.power = min(capacity.borne, card2.power * (5 - game.nb_turn))
            elif capacity.how == "Support":
                card2.power = min(capacity.borne, card2.power + capacity.value * sum(1 for card in game.enemy.cards if card.faction == card2.faction))
            elif capacity.how == "Equalizer":
                card2.power = min(capacity.borne, card2.power + capacity.value * card1.stars)
            elif capacity.how == "nb_pillz_left":
                card2.power += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.power += capacity.value
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
                card2.power = min(capacity.borne, card2.power * game.nb_turn)
                card2.damage = min(capacity.borne, card2.damage * game.nb_turn)
            elif capacity.how == "Degrowth":
                card2.power = min(capacity.borne, card2.power * (5 - game.nb_turn))
                card2.damage = min(capacity.borne, card2.damage * (5 - game.nb_turn))
            elif capacity.how == "Support":
                same_faction_count = sum(1 for card in game.enemy.cards if card.faction == card2.faction)
                card2.power = min(capacity.borne, card2.power + capacity.value * same_faction_count)
                card2.damage = min(capacity.borne, card2.damage + capacity.value * same_faction_count)
            elif capacity.how == "Equalizer":
                card2.power = min(capacity.borne, card2.power + capacity.value * card1.stars)
                card2.damage = min(capacity.borne, card2.damage + capacity.value * card1.stars)
            elif capacity.how == "nb_pillz_left":
                card2.power += capacity.value * game.enemy.pillz
                card2.damage += capacity.value * game.enemy.pillz
            elif capacity.how == "":
                card2.power += capacity.value
                card2.damage += capacity.value
            else:
                raise ValueError(f"Invalid how: {capacity.how} for power_and_damage")
