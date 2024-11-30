from typing import List, Tuple, Any
from card import Card


# class Player:
# 	from typing import List, Tuple, Any

class Player:
	def __init__(self, name: str = "", life: int = -1, pillz: int = -1,
				 cards: List[Any] = None, effect_list: List[Tuple[Any, int, int]] = None):
		"""
		Initialise un joueur avec un nom, des points de vie, des pillz, un tableau de cartes
		et une liste d'effets.

		:param name: Le nom du joueur.
		:param life: Les points de vie du joueur (par défaut -1).
		:param pillz: Les pillz du joueur (par défaut -1).
		:param card_list: La liste des cartes du joueur (par défaut vide).
		:param effect_list: La liste des effets du joueur (par défaut vide).
		"""
		self.name = name
		self.life = life
		self.pillz = pillz
		self.cards = cards if cards is not None else []
		self.effect_list = effect_list if effect_list is not None else []


	@classmethod
	def init_input(self, name: str):
		"""
		Initialise un joueur avec un nom, des points de vie, des pillz, et un tableau de cartes.
		"""
		self.name: str = name
		self.life: int = self._define_stat("life")  # Points de vie
		self.pillz: int = self._define_stat("pillz")  # Points de pillz
		self.card_list: List[Card] = self._initialize_cards()  # Liste des cartes
		self.effect_list: List[Tuple[Any, int, int]] = []  # Liste des effets (type générique pour les effets)

	def _define_stat(self, stat_name: str) -> int:
		"""
		Définit une statistique pour le joueur (par exemple, points de vie ou pillz).
		"""
		while True:
			try:
				value = int(input(f"How many {stat_name.upper()} does {self.name} have? "))
				return value
			except ValueError:
				print("\nYour choice should be a valid number.\n")

	def _initialize_cards(self) -> List[Card]:
		"""
		Initialise la liste des cartes du joueur en demandant les informations nécessaires à l'utilisateur.
		"""
		print(f"\nConfiguring cards for player {self.name}...")
		cards = []
		for i in range(4):  # Exemple : chaque joueur possède 4 cartes
			print(f"\nConfiguring card {i + 1}:")
			card = Card()
			cards.append(card)
		return cards

	def add_effect(self, effect: Any, duration: int, value: int) -> None:
		"""
		Ajoute un effet à la liste des effets du joueur.
		:param effect: Effet appliqué (peut être de tout type).
		:param duration: Durée de l'effet en tours.
		:param value: Valeur associée à l'effet.
		"""
		self.effect_list.append((effect, duration, value))

	def __del__(self):
		"""
		Nettoie les ressources associées au joueur, si nécessaire.
		"""
		print(f"Cleaning up resources for player: {self.name}")

	def __str__(self):
		"""
		Représente les informations du joueur sous forme de chaîne pour un affichage convivial.
		"""
		cards_info = "\n".join([str(card) for card in self.card_list])
		return (f"Player: {self.name}\n"
				f"Life: {self.life}, Pillz: {self.pillz}\n"
				f"Cards:\n{cards_info}")
