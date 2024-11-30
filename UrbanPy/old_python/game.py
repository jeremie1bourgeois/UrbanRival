from player import Player
from card import Card
from game_result import GameResult
from typing import List
import os
import json

class Game:
	def __init__(self):
		"""
		Initialise une nouvelle partie en demandant le tour actuel et à qui appartient le tour.
		"""
		self.nb_turn: int
		self.turn: bool
		self.ally: Player
		self.enemy: Player
		self.history: List[str]
  
	def init_input(self):
		"""
		Initialise une nouvelle partie en demandant le tour actuel et à qui appartient le tour.
		"""
		self.nb_turn: int = 0
		self.turn: bool = False  # True si c'est le tour du joueur allié, False sinon
		self.ally: Player = None  # Instance de Player pour l'allié
		self.enemy: Player = None  # Instance de Player pour l'ennemi
		self.history: List[str] = []  # Historique des actions de jeu

		# Initialisation du numéro du tour
		while True:
			try:
				string_nb_turn = input("What turn are we on? ")
				int_turn = int(string_nb_turn)
				if int_turn < 1 or int_turn > 4:
					print("\nYour choice is out of range. Please choose a number between 1 and 4.\n")
					continue
				self.nb_turn = int_turn
				break
			except ValueError:
				print("\nYour choice should be a valid number.\n")

		# Initialisation de la propriété `turn`
		while True:
			string_turn = input("It's whose turn to play?\nYour turn: 1    ;    His turn: 0\n")
			if string_turn not in ["0", "1"]:
				print('\nYour choice should be "1" or "0".\n')
				continue
			self.turn = string_turn == "1"
			break

		# Initialisation des joueurs
		self.ally = Player("ally")
		self.enemy = Player.init_input("enemy")
   		# Sauvegarde de la configuration initiale
		self.save_initial_configuration()

	def load_initial_configuration(self, file_name: str):
		"""
		Charge une configuration initiale de partie à partir d'un fichier JSON
		et initialise l'objet Game avec ces données.

		:param file_name: Le nom du fichier de configuration à charger (dans le dossier `config_init`).
		"""
		config_dir = "config_init"
		file_path = os.path.join(config_dir, file_name)

		# Vérification que le fichier existe
		if not os.path.exists(file_path):
			raise FileNotFoundError(f"The configuration file {file_name} does not exist in {config_dir}.")

		# Lecture des données depuis le fichier JSON
		with open(file_path, "r") as file:
			game_data = json.load(file)

		# Initialisation des attributs de la partie
		self.nb_turn = game_data["nb_turn"]
		self.turn = game_data["turn"] == "ally"

		# Initialisation des joueurs et de leurs attributs
		self.ally = Player("ally")
		self.enemy = Player("enemy")

		# Initialisation des joueurs et de leurs attributs
		self.ally = Player(name=game_data["ally"]["name"], life=game_data["ally"]["life"], pillz=game_data["ally"]["pillz"])
		self.ally.card_list = [Card(**card_data) for card_data in game_data["ally"]["cards"]]

		self.enemy = Player(name=game_data["enemy"]["name"], life=game_data["enemy"]["life"], pillz=game_data["enemy"]["pillz"])
		self.enemy.card_list = [Card(**card_data) for card_data in game_data["enemy"]["cards"]]

		print(f"Game configuration loaded from {file_path}")


	def save_initial_configuration(self):
		"""
		Sauvegarde la configuration initiale de la partie dans un fichier JSON
		dans le dossier `config_init`. Le fichier est nommé de manière incrémentale.
		"""
		# Création du dossier `config_init` s'il n'existe pas
		config_dir = "config_init"
		if not os.path.exists(config_dir):
			os.makedirs(config_dir)

		# Déterminer le nom du prochain fichier
		files = os.listdir(config_dir)
		max_index = 0
		for file_name in files:
			if file_name.startswith("file_") and file_name.endswith(".json"):
				try:
					# Extraire l'index du fichier
					index = int(file_name.split("_")[1].split(".")[0])
					max_index = max(max_index, index)
				except ValueError:
					continue
		next_file_name = f"file_{max_index + 1}.json"

		# Construire les données à sauvegarder
		game_data = {
			"nb_turn": self.nb_turn,
			"turn": "ally" if self.turn else "enemy",
			"ally": {
				"name": self.ally.name,
				"life": self.ally.life,
				"pillz": self.ally.pillz,
				"cards": [card.__dict__ for card in self.ally.card_list],
			},
			"enemy": {
				"name": self.enemy.name,
				"life": self.enemy.life,
				"pillz": self.enemy.pillz,
				"cards": [card.__dict__ for card in self.enemy.card_list],
			},
		}

		# Sauvegarder les données dans le fichier JSON
		with open(os.path.join(config_dir, next_file_name), "w") as file:
			json.dump(game_data, file, indent=4)

		print(f"Game configuration saved to {os.path.join(config_dir, next_file_name)}")


	def get_card_names(self):
		"""
		Demande à l'utilisateur de saisir les noms des cartes pour le joueur.
		"""
		print("Enter the card names for player 1 and their star counts:")

		for i in range(4):
			while True:
				try:
					card_name: str = input(f"Card {i + 1}: ").strip()
					if not card_name:
						print("Card name cannot be empty. Please try again.")
						continue
					star_count: int = int(input(f"Number of stars for {card_name}: "))
					# Ajouter la carte à un joueur, logique à implémenter selon Player
					# Exemple : self.ally.add_card(card_name, star_count)
					print(f"Added card {card_name} with {star_count} stars.")
					break
				except ValueError:
					print("The number of stars should be a valid integer. Please try again.")

	def check_end(self) -> GameResult:
		"""
		Vérifie si la partie est terminée et renvoie un GameResult.
		"""
		if self.nb_turn == 4:
			if self.ally.health > self.enemy.health:
				return GameResult.ALLY
			elif self.ally.health < self.enemy.health:
				return GameResult.ENEMY
			else:
				return GameResult.DRAW
		elif self.ally.health == 0:
			return GameResult.ENEMY
		elif self.enemy.health == 0:
			return GameResult.ALLY
		else:
			return GameResult.NONE

	def play(self) -> GameResult:
		"""
		Boucle principale du jeu où les tours s'alternent jusqu'à ce qu'il y ait un résultat.
		"""
		result = GameResult.NONE
		while result == GameResult.NONE:
			if self.turn:
				self.ally.play_turn()  # Implémenter la méthode dans Player
			else:
				self.enemy.play_turn()  # Implémenter la méthode dans Player
			self.turn = not self.turn
			self.nb_turn += 1
			result = self.check_end()
		return result
