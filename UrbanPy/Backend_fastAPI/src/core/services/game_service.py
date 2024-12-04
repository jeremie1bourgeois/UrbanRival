import json
import os
from src.core.use_cases.process_round import process_round
from src.core.domain.player import Player
from src.schemas.game_schemas import PlayerCards, ProcessRoundInput
from src.core.domain.card import Card
from enum import Enum
from src.adapters.repositories.game_repository import get_new_game_id, load_game_from_json, save_game_to_json
from src.core.domain.game import Game
from src.utils.config import BASE_DIR

def process_round_service(game_id: str, round_data: ProcessRoundInput):

    # Charger le chemin du fichier de la partie
    game_file_path = os.path.join(BASE_DIR, "data/game/", f"game_data_{game_id}.json")
    os.makedirs(os.path.dirname(game_file_path), exist_ok=True)

    # Charger la partie
    game = load_game_from_json(game_file_path)

    # Jouer un round en passant l'objet round_data
    updated_game = process_round(game, round_data)

    # Sauvegarder la partie mise à jour
    save_game_to_json(updated_game, game_id)
 
    state = check_end(updated_game)

    return (updated_game, state)


class GameResult(Enum):
    ALLY = "Ally Wins"
    ENEMY = "Enemy Wins"
    DRAW = "Draw"
    NONE = "Game Not Finished"

def check_end(board: Game) -> GameResult:
    """
    Vérifie si la partie est terminée et renvoie un GameResult.
    """
    if board.nb_turn == 4:
        if board.ally.life > board.enemy.life:
            return GameResult.ALLY
        elif board.ally.life < board.enemy.life:
            return GameResult.ENEMY
        else:
            return GameResult.DRAW
    elif board.ally.life == 0:
        return GameResult.ENEMY
    elif board.enemy.life == 0:
        return GameResult.ALLY
    else:
        return GameResult.NONE

def create_game(players_cards: PlayerCards) -> Game:
    """
    Crée une partie en initialisant les joueurs avec leurs cartes.

    Args:
        players_cards (PlayerCards): Objet contenant les cartes de `player1` et `player2`.

    Returns:
        Game: Une instance de la classe `Game` initialisée avec les cartes des deux joueurs.
    """
    game = Game(0, True, Player(name="ally", life=12, pillz=12), Player(name="enemy", life=12, pillz=12), [])

    # Ajouter les cartes à player1
    for card_input in players_cards.player1:
        card = Card(card_name=card_input.card_name, nb_stars=card_input.nb_stars)
        game.ally.cards.append(card)

    # Ajouter les cartes à player2
    for card_input in players_cards.player2:
        card = Card(card_name=card_input.card_name, nb_stars=card_input.nb_stars)
        game.enemy.cards.append(card)

    new_id = get_new_game_id()

    # Appeler la fonction pour sauvegarder la partie en JSON
    save_game_to_json(game, new_id)

    return game


def init_game_from_template():
    # Charger le chemin du fichier de la partie
    game_file_path = os.path.join(BASE_DIR, "data/", f"template_game_v1.json")
    os.makedirs(os.path.dirname(game_file_path), exist_ok=True)

    # Charger la partie
    game = load_game_from_json(game_file_path)

    # Générer un nouvel ID pour le jeu
    new_id = get_new_game_id()

    # Sauvegarder la partie en JSON
    save_game_to_json(game, new_id)

    return game