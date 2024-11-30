from game import Game

def process_round(game: Game, player1_card_index: int, player2_card_index: int, player1_pillz: int, player2_pillz: int):
	"""
	Traite un tour de jeu Urban Rivals, en calculant les résultats d'une confrontation entre deux cartes.

	:param game: Instance actuelle de la classe Game.
	:param player1_card_index: Index de la carte jouée par le joueur 1 (allié).
	:param player2_card_index: Index de la carte jouée par le joueur 2 (ennemi).
	:param player1_pillz: Nombre de pillz joués par le joueur 1.
	:param player2_pillz: Nombre de pillz joués par le joueur 2.
	"""
	# Récupération des cartes
	player1_card = game.ally.card_list[player1_card_index]
	player2_card = game.enemy.card_list[player2_card_index]

	# Calcul de l'attaque de chaque joueur
	player1_attack = player1_card.power * (player1_pillz + 1)
	player2_attack = player2_card.power * (player2_pillz + 1)

	# Affichage des informations de debug
	print(f"Player 1 ({game.ally.name}) plays card {player1_card.name} with attack {player1_attack}")
	print(f"Player 2 ({game.enemy.name}) plays card {player2_card.name} with attack {player2_attack}")

	# Déterminer le vainqueur
	if player1_attack > player2_attack:
		game.enemy.life = max(0, game.enemy.life - player1_card.damage)
		print(f"Player 1 wins the round and deals {player1_card.damage} damage to Player 2.")
	elif player2_attack > player1_attack:
		game.ally.life = max(0, game.ally.life - player2_card.damage)
		print(f"Player 2 wins the round and deals {player2_card.damage} damage to Player 1.")
	else:
		print("The round ends in a tie. No damage is dealt.")

	# Mise à jour des pillz
	game.ally.pillz = max(0, game.ally.pillz - player1_pillz)
	game.enemy.pillz = max(0, game.enemy.pillz - player2_pillz)

	# Avancement au tour suivant
	game.nb_turn += 1

	# Affichage des états finaux
	print(f"End of round {game.nb_turn - 1}:")
	print(f"Player 1 (Ally) - Life: {game.ally.life}, Pillz: {game.ally.pillz}")
	print(f"Player 2 (Enemy) - Life: {game.enemy.life}, Pillz: {game.enemy.pillz}")
