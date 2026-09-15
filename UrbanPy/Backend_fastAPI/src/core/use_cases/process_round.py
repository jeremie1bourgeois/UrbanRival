import copy
from src.core.domain.round import Round
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.player import Player
from src.schemas.game_schemas import ProcessRoundInput
from src.core.domain.game import Game, NB_ROUNDS
import src.core.use_cases.apply_capacity_lvl_1 as fct_lvl_1
import src.core.use_cases.apply_capacity_lvl_2 as fct_lvl_2
import src.core.use_cases.apply_capacity_lvl_3 as fct_lvl_3
import src.core.use_cases.apply_capacity_lvl_4 as fct_lvl_4

def process_round(game: Game, round_data: ProcessRoundInput) -> None:
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

        # Le bonus de clan n'est actif que si la main compte au moins 2 cartes du clan
        if not is_clan_bonus_active(game.ally, player1_card):
            player1_card.bonus_fight = None
        if not is_clan_bonus_active(game.enemy, player2_card):
            player2_card.bonus_fight = None
        
        print(f"player1_card: {player1_card}")
        print(f"player2_card: {player2_card}")
        
        if not check_capacity_condition(game, player1_card.ability_fight, True, round_data.player1_card_index, round_data.player2_card_index):
            player1_card.ability_fight = None
        if not check_capacity_condition(game, player1_card.bonus_fight, True, round_data.player1_card_index, round_data.player2_card_index):
            player1_card.bonus_fight = None
        if not check_capacity_condition(game, player2_card.ability_fight, False, round_data.player2_card_index, round_data.player1_card_index):
            player2_card.ability_fight = None
        if not check_capacity_condition(game, player2_card.bonus_fight, False, round_data.player2_card_index, round_data.player1_card_index):
            player2_card.bonus_fight = None

        # Appliquer les effets de combat
        fct_lvl_1.apply_capacity_lvl_1(player1_card, player2_card)
        fct_lvl_2.apply_capacity_lvl_2(game, player1_card, player2_card)

        # Appliquer les fury
        if player1_card.fury:
            player1_card.damage_fight += 2
        if player2_card.fury:
            player2_card.damage_fight += 2

        # Calculer les attaques
        player1_card.attack += (player1_card.power_fight * round_data.player1_pillz)
        player2_card.attack += (player2_card.power_fight * round_data.player2_pillz)

        # Créer une nouvelle instance de Round
        round_result = Round()
        round_result.ally.card_index = round_data.player1_card_index  # Stocker l'index de la carte
        round_result.enemy.card_index = round_data.player2_card_index  # Stocker l'index de la carte

        # Résoudre le combat
        resolve_combat(game, player1_card, player2_card, round_result)
        
        # Un joueur tombé à 0 vie a perdu avant les effets de fin de round, sauf s'il est réanimé
        if game.ally.life <= 0 or game.enemy.life <= 0:
            fct_lvl_3.apply_reanimate(game, player1_card, player2_card)
        if game.ally.life > 0 and game.enemy.life > 0:
            fct_lvl_3.apply_capacity_lvl_3(game, player1_card, player2_card)
            fct_lvl_4.apply_capacity_lvl_4(game, game.ally, game.enemy, player1_card, player2_card)

        # Ajouter le round au history
        game.history.append(round_result)
    
        # Mettre à jour le tour
        player1_card.played = True
        player2_card.played = True

        game.nb_turn += 1
        game.turn = not game.turn

    except Exception as e:
        print(f"Exception in process_round: {e}")
        raise e


def resolve_combat(game: Game, player1_card: Card, player2_card: Card, round_result: Round):
    if player1_card.attack > player2_card.attack:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage_fight)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    elif player2_card.attack > player1_card.attack:
        game.ally.life = max(0, game.ally.life - player2_card.damage_fight)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True
    elif player1_card.stars < player2_card.stars:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage_fight)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    elif player2_card.stars < player1_card.stars:
        game.ally.life = max(0, game.ally.life - player2_card.damage_fight)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True
    elif game.turn:
        game.enemy.life = max(0, game.enemy.life - player1_card.damage_fight)
        round_result.ally.win = True
        round_result.enemy.win = False
        player1_card.win = True
        player2_card.win = False
    else:
        game.ally.life = max(0, game.ally.life - player2_card.damage_fight)
        round_result.ally.win = False
        round_result.enemy.win = True
        player1_card.win = False
        player2_card.win = True


DEFERRED_CONDITIONS = {"defeat", "backlash", "victory_defeat"}  # évaluées après le combat (niveau 3)


def check_capacity_condition(game: Game, capacity: Capacity, is_ally: bool, own_card_index: int, opp_card_index: int) -> bool:
    """
    Vérifie (et consomme) les conditions de début de round d'une capacité de combat.
    own_card_index / opp_card_index : index de la carte jouée par le joueur qui possède la capacité / par son adversaire.
    Retourne False si une condition n'est pas remplie ; les conditions différées au niveau 3 sont laissées en place.
    """
    if capacity is None or not capacity.effect_conditions:
        return True

    own_player = game.ally if is_ally else game.enemy
    last_round = game.history[-1] if game.history else None
    own_won_last_round = None if last_round is None else (last_round.ally.win if is_ally else last_round.enemy.win)
    plays_first = game.turn if is_ally else not game.turn

    checks = {
        "revenge": lambda: own_won_last_round is False,
        "confidence": lambda: own_won_last_round is True,
        "courage": lambda: plays_first,
        "reprisal": lambda: not plays_first,
        "symmetry": lambda: own_card_index == opp_card_index,
        "asymmetry": lambda: own_card_index != opp_card_index,
    }

    for condition in list(capacity.effect_conditions):
        if condition in checks:
            if not checks[condition]():
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("bet"):
            if own_player.cards[own_card_index].pillz_fight <= _bet_threshold(condition):
                return False
            capacity.effect_conditions.remove(condition)
        elif condition not in DEFERRED_CONDITIONS:
            raise ValueError(f"Invalid effect_conditions (check_capacity_condition): {capacity.effect_conditions}")
    return True


def _bet_threshold(bet: str) -> int:
    """Extrait le seuil X d'une condition "bet X"."""
    return int(bet[3:].strip())


MIN_CLAN_CARDS_FOR_BONUS = 2


def is_clan_bonus_active(player: Player, card: Card) -> bool:
    """Règle Urban Rivals : le bonus de clan s'active si la main (les 4 cartes) compte au moins 2 cartes du clan."""
    return sum(1 for c in player.cards if c.faction == card.faction) >= MIN_CLAN_CARDS_FOR_BONUS


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
    if game.nb_turn > NB_ROUNDS or game.ally.life <= 0 or game.enemy.life <= 0:
        raise ValueError("Game is already finished.")
