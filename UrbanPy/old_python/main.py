from game import Game
from game_result import GameResult

def main():
    # Crée une instance du jeu
    game = Game()
    
    game.load_initial_configuration("file_1.json")
    
    result = game.play()

    # Affiche le résultat de la partie
    if result == GameResult.ALLY:
        print("The winner is: Player 1 (Ally)!")
    elif result == GameResult.ENEMY:
        print("The winner is: Player 2 (Enemy)!")
    elif result == GameResult.DRAW:
        print("The game ended in a draw!")
    else:
        print("The game could not be completed.")

if __name__ == "__main__":
    main()
