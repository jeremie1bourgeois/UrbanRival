import os
from src.core.use_cases.process_round import process_round
from src.core.domain.player import Player
from src.schemas.game_schemas import PlayerCards, ProcessRoundInput
from src.core.domain.card import Card

from src.adapters.repositories.game_repository import get_new_game_id, load_game_from_json, save_game_to_json
from src.core.domain.game import Game
from src.utils.config import BASE_DIR

def process_round_service(game_id: str, round_data: ProcessRoundInput):
	# Charger le chemin du fichier de la partie
	game_file_path = os.path.join(BASE_DIR, "data/game/", f"game_data_{game_id}.json")
	os.makedirs(os.path.dirname(game_file_path), exist_ok=True)
	print("game_file_path", game_file_path)
	# Charger la partie
	game = load_game_from_json(game_file_path)

	# Jouer un round en passant l'objet round_data
	updated_game = process_round(game, round_data)
	print("updated_game", updated_game)
	# Sauvegarder la partie mise à jour
	save_game_to_json(updated_game, game_id)

	return updated_game



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
