"""
Moteur de référence sur le contrat : les fonctions pures que l'IA appelle (legal_actions, step, terminal), réalisées
par process_round. Sans effet de bord : step reconstruit une partie depuis l'état compact, la joue et renvoie le
nouvel état. Un moteur compilé expose les mêmes fonctions sur les mêmes types et doit donner les mêmes résultats.
"""
from typing import List, Optional

from src.core.domain.game import NB_ROUNDS
from src.core.engine.contract import Action, Deck, State, game_from_state, state_from_game
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import ProcessRoundInput

FURY_COST = 3


def legal_actions(state: State, side: str) -> List[Action]:
    """Cartes non jouées x pillz_fight de 1 (aucune mise) à pillz + 1 x fury si la mise + 3 tient dans les pillz."""
    player = state.ally if side == "ally" else state.enemy
    actions = []
    for index, played in enumerate(player.played):
        if played:
            continue
        for bet in range(player.pillz + 1):
            actions.append(Action(index, bet + 1, False))
            if bet + FURY_COST <= player.pillz:
                actions.append(Action(index, bet + 1, True))
    return actions


def step(deck: Deck, state: State, ally_action: Action, enemy_action: Action) -> State:
    game = game_from_state(deck, state)
    round_data = ProcessRoundInput(player1_card_index=ally_action.card, player1_pillz=ally_action.pillz,
                                   player1_fury=ally_action.fury, player2_card_index=enemy_action.card,
                                   player2_pillz=enemy_action.pillz, player2_fury=enemy_action.fury)
    check_round_correct(game, round_data)
    process_round(game, round_data)
    return state_from_game(game)


def terminal(state: State) -> Optional[float]:
    """1 / 0,5 / 0 pour l'allié si la partie est finie (même règle que game_service.check_end), None sinon."""
    if state.nb_turn > NB_ROUNDS:
        if state.ally.life != state.enemy.life:
            return 1.0 if state.ally.life > state.enemy.life else 0.0
        return 0.5
    if state.ally.life == 0:
        return 0.0
    if state.enemy.life == 0:
        return 1.0
    return None
