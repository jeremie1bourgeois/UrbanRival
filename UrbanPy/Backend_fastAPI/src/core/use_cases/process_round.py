from src.schemas.game_schemas import ProcessRoundInput
from src.core.domain.game import Game

from src.core.domain.game import Game

def process_round(game: Game, round_data: ProcessRoundInput) -> Game:
    try:
        # Vérifier les indices des cartes
        if not (0 <= round_data.player1_card_index < len(game.ally.cards)):
            raise ValueError(f"Invalid player1_card_index: {round_data.player1_card_index}")
        if not (0 <= round_data.player2_card_index < len(game.enemy.cards)):
            raise ValueError(f"Invalid player2_card_index: {round_data.player2_card_index}")

        # Vérifier le nombre de pillz
        if round_data.player1_pillz > game.ally.pillz:
            raise ValueError(f"Player 1 does not have enough pillz: {round_data.player1_pillz}")
        if round_data.player2_pillz > game.enemy.pillz:
            raise ValueError(f"Player 2 does not have enough pillz: {round_data.player2_pillz}")

        # Récupérer les cartes sélectionnées
        player1_card = game.ally.cards[round_data.player1_card_index]
        player2_card = game.enemy.cards[round_data.player2_card_index]

        # Calculer les attaques
        player1_attack = player1_card.power * (round_data.player1_pillz + 1)
        player2_attack = player2_card.power * (round_data.player2_pillz + 1)

        # Résoudre le combat
        if player1_attack > player2_attack:
            game.enemy.life = max(0, game.enemy.life - player1_card.damage)
        elif player2_attack > player1_attack:
            game.ally.life = max(0, game.ally.life - player2_card.damage)

        # Mettre à jour les pillz et le tour
        game.ally.pillz = max(0, game.ally.pillz - round_data.player1_pillz)
        game.enemy.pillz = max(0, game.enemy.pillz - round_data.player2_pillz)
        game.nb_turn += 1

        return game
    except Exception as e:
        print(f"Exception in process_round: {e}")
        raise

