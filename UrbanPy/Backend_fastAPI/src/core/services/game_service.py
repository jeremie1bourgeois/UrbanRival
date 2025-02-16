import os
from src.core.use_cases.process_round import check_round_correct, process_round
from src.core.domain.player import Player
from src.schemas.game_schemas import GameResult, PlayerCards, ProcessRoundInput
from src.core.domain.card import Card
from src.adapters.repositories.game_repository import get_new_game_id, get_new_test_id, load_game_from_json, save_game_to_json
from src.core.domain.game import Game
from src.utils.config import BASE_DIR

def process_round_service(game_id: str, round_data: ProcessRoundInput):
    # Charger le chemin du dossier de la partie
    game_directory = os.path.join(BASE_DIR, "data/game/", f"game_{game_id}")

    # Vérifier si le dossier existe
    if not os.path.exists(game_directory):
        raise FileNotFoundError(f"Game directory not found: {game_directory}")

    # Trouver le fichier avec le nb_turn le plus élevé
    game_files = [f for f in os.listdir(game_directory) if f.startswith(f"game_data_{game_id}_") and f.endswith(".json")]
    if not game_files:
        raise FileNotFoundError(f"No game files found in directory: {game_directory}")

    # Extraire le nb_turn de chaque fichier et trouver le maximum
    max_turn_file = max(game_files, key=lambda x: int(x.split("_")[3].split(".")[0]))
    game_file_path = os.path.join(game_directory, max_turn_file)

    # Charger la partie
    game = load_game_from_json(game_file_path)
    
    # Vérifier si le round est correct
    check_round_correct(game, round_data)

    # Jouer un round en passant l'objet round_data
    process_round(game, round_data)

    # Sauvegarder la partie mise à jour dans le dossier correspondant
    save_game_to_json(game, game_id, game_directory)

    # Vérifier l'état de la partie (fin de partie ou non)
    state = check_end(game)

    return (game, state)



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

    # Créer un dossier spécifique pour cette partie
    game_directory = os.path.join("data", "game", f"game_{new_id}")
    os.makedirs(game_directory, exist_ok=True)

    # Appeler la fonction pour sauvegarder la partie en JSON dans le dossier créé
    save_game_to_json(game, new_id, game_directory)

    return game


def init_game_from_template():
    """
    Initialise une nouvelle partie à partir d'un template et sauvegarde le fichier JSON avec le nombre de tours.
    """
    # Charger le chemin du fichier de la partie
    game_file_path = os.path.join(BASE_DIR, "data/", f"template_game_v1.json")
    os.makedirs(os.path.dirname(game_file_path), exist_ok=True)

    # Charger la partie
    game = load_game_from_json(game_file_path)

    # Générer un nouvel ID pour le jeu
    new_id = get_new_game_id()

    # Créer un dossier spécifique pour cette partie
    game_directory = os.path.join("data", "game", f"game_{new_id}")
    os.makedirs(game_directory, exist_ok=True)

    # Appeler la fonction pour sauvegarder la partie en JSON dans le dossier créé
    save_game_to_json(game, new_id, game_directory)

    return (game, new_id)

def save_for_test_service(game_id: int):
    """
    Crée une sauvegarde d'une situation A d'une partie, d'un play des joueurs et de la situation B qui en découle.
    (Est appelé lorsque un round s'est déroulé comme prévue et que l'on souhaite sauvegarder les données pour les tests.)
    """
    # Charger le chemin du dossier de la partie
    game_directory = os.path.join(BASE_DIR, "data/game/", f"game_{game_id}")

    # Vérifier si le dossier existe
    if not os.path.exists(game_directory):
        raise FileNotFoundError(f"Game directory not found: {game_directory}")

    # Trouver le fichier avec le nb_turn le plus élevé
    game_files = [f for f in os.listdir(game_directory) if f.startswith(f"game_data_{game_id}_") and f.endswith(".json")]

    if not game_files:
        raise FileNotFoundError(f"No game files found in directory: {game_directory}")

    # Extraire le nb_turn de chaque fichier et trouver le maximum
    curr_turn_file = max(game_files, key=lambda x: int(x.split("_")[3].split(".")[0]))
    
    curr_nb_round: int = int(curr_turn_file.split('_')[3].split('.')[0])
    if curr_nb_round < 2:
        raise ValueError("Not enough turns to save for test.")

    prev_turn_file = f"game_data_{game_id}_{curr_nb_round}.json"

    curr_game_file_path = os.path.join(game_directory, curr_turn_file)
    prev_game_file_path = os.path.join(game_directory, prev_turn_file)

    # Charger la partie
    curr_game_round = load_game_from_json(curr_game_file_path)
    prev_game_round = load_game_from_json(prev_game_file_path)

    save_play_on_json(curr_game_round, prev_game_round)
    
def save_play_on_json(curr_game_round: Game, prev_game_round: Game):
    """
    Sauvegarde les données d'une partie, d'un play des joueurs et de la situation B qui en découle.
    L'id du test est le plus grand id des tests qui existe + 1.
    """
    # Créer un dossier spécifique pour cette sauvegarde
    save_directory = os.path.join(BASE_DIR, "data/test/", f"test_{get_new_test_id()}")
    os.makedirs(save_directory, exist_ok=True)
    
    # Sauvegarder la partie actuelle
    save_game_to_json(curr_game_round, "curr", save_directory)
    
    # Sauvegarder la partie précédente
    save_game_to_json(prev_game_round, "prev", save_directory)
