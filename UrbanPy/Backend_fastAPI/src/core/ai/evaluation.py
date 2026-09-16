"""
Évaluation d'un état de partie pour un camp : la note que maximisent les adversaires de recherche
(`opponent.greedy_pick`, `opponent.minimax_pick`) et l'étalon auquel comparer, plus tard, un réseau appris.

La partie se gagne aux vies : l'écart de vies pèse le plus lourd, les pillz et les cartes encore en main sont
des ressources qui ne comptent que par ce qu'elles permettront de gagner ensuite. Les poids sont volontairement
grossiers (réglés au banc d'essai `scripts/ai_arena.py`) : ils n'ont pas à être justes, seulement à ordonner
correctement deux coups possibles.

Réglage (60 parties par mesure, mains tirées au hasard, vie 5 / main 0,5) — le poids des pillz est le point
sensible, une pillz gagne ~1,3 vie plus tard dans la partie :

| poids pillz | glouton / heuristique | glouton / aléatoire | minimax / heuristique | minimax / aléatoire |
|---|---|---|---|---|
| 1 | 12 % | 60 % | 53 % | 61 % |
| 3 | 73 % | 84 % | 66 % | 69 % |
| **4** | **62 %** | **84 %** | **73 %** | **83 %** |
| 5 | 51 % | 78 % | 68 % | 82 % |

Ces poids sont une approximation provisoire : le solveur d'équilibre les remplacera par la vraie valeur
d'un état (voir le plan « IA imbattable en ELO »).
"""
from src.core.ai.engine import is_terminal, player, reward
from src.core.domain.player import Player

WIN_SCORE = 1000.0      # une partie gagnée vaut plus que n'importe quel avantage matériel
LIFE_WEIGHT = 5.0
PILLZ_WEIGHT = 4.0      # une pillz vaut presque une vie : la brader au round 1 perd les trois suivants
HAND_WEIGHT = 0.5       # par point de (puissance + dégâts) des cartes non jouées


def evaluate(state, side: str) -> float:
    """Note de l'état pour `side` (« ally » / « enemy ») : positive s'il est en bonne posture."""
    if is_terminal(state):
        return WIN_SCORE * reward(state, side)
    own, opp = player(state, side), player(state, _other(side))
    return (LIFE_WEIGHT * (own.life - opp.life)
            + PILLZ_WEIGHT * (own.pillz - opp.pillz)
            + HAND_WEIGHT * (hand_value(own) - hand_value(opp)))


def hand_value(player_: Player) -> int:
    """Valeur brute des cartes qui restent à jouer : puissance + dégâts, sans tenir compte des pouvoirs."""
    return sum(card.power + card.damage for card in player_.cards if not card.played)


def _other(side: str) -> str:
    return "enemy" if side == "ally" else "ally"
