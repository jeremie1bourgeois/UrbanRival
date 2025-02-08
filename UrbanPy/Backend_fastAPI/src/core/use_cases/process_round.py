import copy
from src.core.domain.round import Round
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.schemas.game_schemas import ProcessRoundInput
from src.core.domain.game import Game
import src.core.use_cases.apply_capacity_lvl_1 as fct_lvl_1
import src.core.use_cases.apply_capacity_lvl_2 as fct_lvl_2
import src.core.use_cases.apply_capacity_lvl_3 as fct_lvl_3
import src.core.use_cases.apply_capacity_lvl_4 as fct_lvl_4

def process_round(game: Game, round_data: ProcessRoundInput) -> Game:
    try:
        # Mise à jour des pillz
        game.ally.pillz -= ((round_data.player1_pillz - 1) + 3 * round_data.player1_fury) # -1 car 1 pillz est toujours consommée
        game.enemy.pillz -= ((round_data.player2_pillz - 1) + 3 * round_data.player2_fury) # -1 car 1 pillz est toujours consommée

        # Récupérer les cartes sélectionnées
        player1_card = game.ally.cards[round_data.player1_card_index]
        player2_card = game.enemy.cards[round_data.player2_card_index]

        # Initialiser les données de combat
        init_fight_data(player1_card, round_data.player1_pillz, round_data.player1_fury)
        init_fight_data(player2_card, round_data.player2_pillz, round_data.player2_fury)

        # Appliquer les effets de combat
        fct_lvl_1.apply_capacity_lvl_1(player1_card, player2_card)
        fct_lvl_2.apply_capacity_lvl_2(game, player1_card, player2_card)

        # Appliquer les fury
        if player1_card.fury:
            player1_card.damage_fight += 2
        if player2_card.fury:
            player2_card.damage_fight += 2

        # Calculer les attaques
        player1_card.attack = player1_card.power_fight * round_data.player1_pillz
        player2_card.attack = player2_card.power_fight * round_data.player2_pillz

        # Créer une nouvelle instance de Round
        round_result = Round()
        round_result.ally.card_index = round_data.player1_card_index  # Stocker l'index de la carte
        round_result.enemy.card_index = round_data.player2_card_index  # Stocker l'index de la carte

        # Résoudre le combat
        resolve_combat(game, player1_card, player2_card, round_result)

        # Appliquer les effets de combat
        fct_lvl_3.apply_capacity_lvl_3(game, player1_card, player2_card)
        fct_lvl_4.apply_capacity_lvl_4(game, game.ally, game.enemy, player1_card, player2_card)

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


def resolve_combat(game: Game, player1_card: Card, player2_card: Card, round_result: Round):
    if player1_card.attack > player2_card.attack:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    elif player2_card.attack > player1_card.attack:
        game.ally.life = max(0, game.ally.life - player2_card.damage)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True
    elif player1_card.stars < player2_card.stars:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    elif player2_card.stars < player1_card.stars:
        game.ally.life = max(0, game.ally.life - player2_card.damage)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True
    elif game.turn:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    else:
        game.ally.life = max(0, game.ally.life - player2_card.damage)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True


def check_capacity_condition(game: Game, capacity: Capacity, is_ally: bool, ally_card_index: int, enemy_card_index: int) -> Capacity:
    if capacity.condition_effect is None:
        return capacity
    if is_ally:
        if capacity.condition_effect == "Revenge":
            return capacity if game.history and game.history[-1].ally.win == False else None
        elif capacity.condition_effect == "Reprisal":
            return capacity if game.turn == False else None
        elif capacity.condition_effect == "Confidence":
            return capacity if game.history and game.history[-1].ally.win == True else None
        elif capacity.condition_effect == "Courage":
            return capacity if game.turn == True else None
        elif capacity.condition_effect == "Symmetry":
            return capacity if ally_card_index == enemy_card_index else None
        elif capacity.condition_effect == "Asymmetry":
            return capacity if ally_card_index != enemy_card_index else None
        elif capacity.condition_effect.startswith("Bet"):
            return capacity if game.ally.cards[ally_card_index].pillz_fight > int(capacity.condition_effect[3:]) else None
        else:
            raise ValueError(f"Invalid condition_effect (check_capacity_condition): {capacity.condition_effect}")
    else:
        if capacity.condition_effect == "Revenge":
            return capacity if game.history and game.history[-1].enemy.win == False else None
        elif capacity.condition_effect == "Reprisal":
            return capacity if game.turn == True else None
        elif capacity.condition_effect == "Confidence":
            return capacity if game.history and game.history[-1].enemy.win == True else None
        elif capacity.condition_effect == "Courage":
            return capacity if game.turn == False else None
        elif capacity.condition_effect == "Symmetry":
            return capacity if ally_card_index == enemy_card_index else None
        elif capacity.condition_effect == "Asymmetry":
            return capacity if ally_card_index != enemy_card_index else None
        elif capacity.condition_effect == "Bet":
            return capacity if game.enemy.cards[enemy_card_index].pillz_fight > capacity.borne else None
        else:
            raise ValueError(f"Invalid condition_effect (check_capacity_condition): {capacity.condition_effect}")



def init_fight_data(card: Card, nb_pillz: int, fury: bool):
    card.power_fight = card.power
    card.damage_fight = card.damage
    card.ability_fight = copy.deepcopy(card.ability)
    card.bonus_fight = copy.deepcopy(card.bonus)
    card.pillz_fight = nb_pillz
    card.fury = fury
    card.attack = 0



def check_round_correct(game: Game, round_data: ProcessRoundInput):
    if round_data.player1_card_index >= 4:
        raise ValueError("Player 1: invalid card index.")
    if round_data.player2_card_index >= 4:
        raise ValueError("Player 2: invalid card index.")
    if round_data.player1_pillz + 3 * round_data.player1_fury > game.ally.pillz + 1:
        raise ValueError("Player 1: too many pillz.")
    if round_data.player2_pillz + 3 * round_data.player2_fury > game.enemy.pillz + 1:
        raise ValueError("Player 2: too many pillz.")
    if game.ally.cards[round_data.player1_card_index].played:
        raise ValueError("Player 1: card already played.")
    if game.enemy.cards[round_data.player2_card_index].played:
        raise ValueError("Player 2: card already played.")
