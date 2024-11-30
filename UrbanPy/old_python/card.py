import json
import os


class Card:
	def __init__(self):
		"""
		Initialise une carte avec un nom, une faction, un bonus, un nombre d'étoiles, une puissance, des dégâts,
		une capacité, une puissance de combat, des dégâts de combat, une capacité de combat, un bonus de combat,
		des pillz de combat, une attaque et un indicateur de jouabilité.
		"""
		self.name: str
		self.faction: str
		self.bonus: str
		self.stars: int
		self.power: int
		self.damage: int
		self.ability: str
		self.power_fight: int
		self.damage_fight: int
		self.ability_fight: str
		self.bonus_fight: str
		self.pillz_fight: int
		self.attack: int
		self.played: int
  
	def __init__(self, **kwargs):
		"""
		Initialise une carte avec des attributs optionnels depuis un dictionnaire.
		Les attributs absents dans le dictionnaire seront initialisés avec des valeurs par défaut.
		"""
		self.name: str = kwargs.get("name", "")
		self.faction: str = kwargs.get("faction", "")
		self.bonus: str = kwargs.get("bonus", "")
		self.stars: int = kwargs.get("stars", 0)
		self.power: int = kwargs.get("power", 0)
		self.damage: int = kwargs.get("damage", 0)
		self.ability: str = kwargs.get("ability", "")
		self.power_fight: int = kwargs.get("power_fight", 0)
		self.damage_fight: int = kwargs.get("damage_fight", 0)
		self.ability_fight: str = kwargs.get("ability_fight", "")
		self.bonus_fight: str = kwargs.get("bonus_fight", "")
		self.pillz_fight: int = kwargs.get("pillz_fight", 0)
		self.attack: int = kwargs.get("attack", 0)
		self.played: int = kwargs.get("played", 0)


	def init_input(self):
		"""
		Initialise une carte en demandant à l'utilisateur son nom, ses étoiles et d'autres attributs
		à partir des données d'un fichier JSON.
		"""
		self.name: str = ""
		self.faction: str = ""
		self.bonus: str = ""
		self.stars: int = 0
		self.power: int = 0
		self.damage: int = 0
		self.ability: str = ""
		self.power_fight: int = 0
		self.damage_fight: int = 0
		self.ability_fight: str = ""
		self.bonus_fight: str = ""
		self.pillz_fight: int = 0
		self.attack: int = 0
		self.played: int = 0

		self.initialize_card()

	def initialize_card(self):
		"""
		Configure une carte en demandant les données nécessaires à l'utilisateur et en chargeant les informations
		depuis un fichier JSON.
		"""
		json_path = "jsonData_officiel.json"

		# Vérifier l'existence du fichier JSON
		if not os.path.exists(json_path):
			print("Error: JSON file not found.")
			return

		with open(json_path, 'r') as file:
			data = json.load(file)

		# Saisie et recherche du nom de la carte
		self.name = self._get_card_name(data)

		# Récupérer les informations de la carte depuis le JSON
		card_data = data[self.name]
		self.faction = card_data.get("faction", "")
		self.bonus = card_data.get("bonus", "")

		# Saisie du nombre d'étoiles et récupération des données associées
		self.stars = self._get_card_stars(card_data)
		star_data = card_data[str(self.stars)]
		self.power = int(star_data.get("power", 0))
		self.damage = int(star_data.get("damage", 0))
		self.ability = star_data.get("ability", "")

	def _get_card_name(self, data: dict) -> str:
		"""
		Demande à l'utilisateur de saisir le nom de la carte et vérifie sa validité dans le JSON.
		"""
		while True:
			card_name = input("\nWhat's the name of your card? ").strip()
			if not card_name:
				print("Card name cannot be empty. Please try again.")
				continue

			matching_keys = [
				key for key in data.keys()
				if key.lower().startswith(card_name.lower())
			]

			if len(matching_keys) == 1:
				print(f"Card found: {matching_keys[0]}")
				return matching_keys[0]

			elif len(matching_keys) > 1:
				print("\nMultiple matches found:")
				for idx, key in enumerate(matching_keys, 1):
					print(f"{idx}: {key}")

				choice = input("Please choose your card by number or type 'no' to retry: ").strip()
				if choice.lower() == "no":
					continue

				if choice.isdigit():
					choice_idx = int(choice) - 1
					if 0 <= choice_idx < len(matching_keys):
						print(f"Card found: {matching_keys[choice_idx]}")
						return matching_keys[choice_idx]

				print("Invalid choice. Please try again.")
			else:
				print("No matching cards found. Please try again.")

	def _get_card_stars(self, card_data: dict) -> int:
		"""
		Demande à l'utilisateur de saisir le nombre d'étoiles pour la carte et vérifie sa validité.
		"""
		while True:
			try:
				stars = int(input("\nHow many stars does your card have? ").strip())
				if str(stars) in card_data:
					return stars
				else:
					print("This number of stars doesn't exist for this card. Please try again.")
			except ValueError:
				print("Your choice should be a valid number. Please try again.")

	def __str__(self):
		"""
		Représente la carte sous forme de chaîne pour un affichage convivial.
		"""
		return (f"Name: {self.name}, Faction: {self.faction}, Stars: {self.stars}, "
				f"Power: {self.power}, Damage: {self.damage}, Ability: {self.ability}, "
				f"Bonus: {self.bonus}")
