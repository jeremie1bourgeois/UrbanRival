"""
Matrice de round rapide (docs/IA.md, étape 3) : l'issue de toutes les mises d'un couple de cartes sans rejouer le
round entier à chaque cellule. Le moteur reste la seule source de vérité — on évite de le rejouer, on ne le
réécrit pas :

1. **une** phase de préparation (`process_round.prepare_fight`) sur une copie de l'état : pouvoirs, Stops,
   modificateurs de puissance et de dégâts ;
2. les attaques de toutes les mises **en numpy** — puissance × pillz, puis les modificateurs d'attaque survivants,
   lus sur les cartes préparées et appliqués dans l'ordre du moteur, bornes comprises — d'où le vainqueur de
   chaque cellule (égalités : Tie-break, étoiles, premier joueur, comme `resolve_combat`) ;
3. les cellules se groupent en **classes d'issue** (fury de chacun, vainqueur) : le moteur ne rejoue le round
   qu'une fois par classe (≤ 8), et les autres cellules de la classe n'en diffèrent que par les pillz restantes.

**Repli obligatoire** vers le moteur, cellule par cellule, dès qu'une capacité en jeu lit la mise ou les pillz
(`bet_sensitive`) : le raccourci ne s'autorise que là où il est prouvé identique — voir
tests/test_ai_round_matrix.py et scripts/round_matrix_sweep.py.
"""
from typing import Callable, Dict, Tuple

import numpy as np

from src.core.ai import engine
from src.core.ai.engine import Pick
from src.core.domain.card import FIGHT_SLOTS
from src.core.domain.game import Game
from src.core.use_cases import process_round as rules
from src.core.use_cases.multipliers import multiplier
from src.schemas.game_schemas import ProcessRoundInput

# Ce qui lit la mise ou les pillz restantes (vocabulaire fermé du parseur, voir docs/IA.md étape 3) :
# la matrice rapide ne s'en mêle pas, le moteur rejoue chaque cellule.
SENSITIVE_TYPES = {"pillz", "recover", "dope", "consume", "repair", "combust", "tune_out"}
SENSITIVE_HOWS = {"nb_pillz_left", "nb_pillz_lost", "tune_out"}
SENSITIVE_CONDITIONS = ("bet", "killshot", "perfect")
SENSITIVE_EFFECTS = {"dope", "repair", "consume", "combust"}

Leaf = Callable[[Game], object]


def bet_sensitive(state: Game) -> bool:
    """Vrai si une capacité des deux mains, ou un effet persistant, lit la mise ou les pillz : pas de raccourci."""
    for player in (state.ally, state.enemy):
        if any(effect.kind in SENSITIVE_EFFECTS for effect in player.effect_list):
            return True
        for card in player.cards:
            for capacity in (card.ability, card.bonus):
                if capacity is None:
                    continue
                if SENSITIVE_TYPES & set(capacity.types) or capacity.how in SENSITIVE_HOWS:
                    return True
                if any(condition.startswith(SENSITIVE_CONDITIONS) for condition in capacity.effect_conditions):
                    return True
    return False


def values(state: Game, first: str, card_first: int, card_second: int, leaf: Leaf) -> Dict[Tuple[Pick, Pick], object]:
    """
    `leaf(état suivant)` pour chaque couple (choix du premier joueur sur `card_first`, choix du second sur
    `card_second`). L'état passé à `leaf` est **temporaire** (un représentant de classe dont les pillz sont
    ajustées le temps de l'appel) : `leaf` doit en lire ce qu'il veut, pas le conserver.
    """
    second = engine.other(first)
    rows = [pick for pick in engine.legal_actions(state, first) if pick.card_index == card_first]
    columns = [pick for pick in engine.legal_actions(state, second) if pick.card_index == card_second]
    if bet_sensitive(state):
        return {(row, column): leaf(engine.next_state(state, first, row, column)) for row in rows for column in columns}

    ally_card, enemy_card = (card_first, card_second) if first == "ally" else (card_second, card_first)
    ally_wins = winner_matrix(state, ally_card, enemy_card)
    representatives = {}
    result = {}
    for row in rows:
        for column in columns:
            ally_pick, enemy_pick = (row, column) if first == "ally" else (column, row)
            ally_bet, enemy_bet = ally_pick.pillz - 1, enemy_pick.pillz - 1
            outcome = (ally_pick.fury, enemy_pick.fury, bool(ally_wins[ally_bet, enemy_bet]))
            if outcome not in representatives:
                after, _ = engine.step(state, ally_pick, enemy_pick, log=False)
                representatives[outcome] = (after, ally_bet, enemy_bet)
            after, class_ally_bet, class_enemy_bet = representatives[outcome]
            after.ally.pillz += class_ally_bet - ally_bet
            after.enemy.pillz += class_enemy_bet - enemy_bet
            try:
                result[(row, column)] = leaf(after)
            finally:
                after.ally.pillz -= class_ally_bet - ally_bet
                after.enemy.pillz -= class_enemy_bet - enemy_bet
    return result


def winner_matrix(state: Game, ally_card: int, enemy_card: int) -> np.ndarray:
    """
    `[mise alliée, mise ennemie] -> l'allié gagne le round`, pour toutes les mises (0..pillz de chaque côté), la fury
    ne changeant pas les attaques. Une préparation du moteur, puis les attaques en numpy.
    """
    scratch = engine.clone(state)
    ally, enemy = rules.prepare_fight(scratch, ProcessRoundInput(
        player1_card_index=ally_card, player1_pillz=1, player2_card_index=enemy_card, player2_pillz=1))
    attacks = {id(ally): ally.power_fight * np.arange(1, state.ally.pillz + 2),
               id(enemy): enemy.power_fight * np.arange(1, state.enemy.pillz + 2)}
    # Modificateurs d'attaque, dans l'ordre de apply_capacity_lvl_2 : cible ally, both, enemy ; allié puis ennemi ; par emplacement.
    for target in ("ally", "both", "enemy"):
        for card, opp_card, own, opp in ((ally, enemy, scratch.ally, scratch.enemy), (enemy, ally, scratch.enemy, scratch.ally)):
            for slot in FIGHT_SLOTS:
                capacity = getattr(card, slot)
                if capacity is None or capacity.target != target or "attack" not in capacity.types:
                    continue
                bonus = capacity.value * multiplier(capacity.how, scratch, own, opp, card, opp_card)
                targets = {"ally": (card,), "enemy": (opp_card,), "both": (card, opp_card)}[target]
                for modified in targets:
                    attacks[id(modified)] = _apply_to(attacks[id(modified)], bonus, capacity.borne, capacity.value > 0)
    ally_attack, enemy_attack = attacks[id(ally)][:, None], attacks[id(enemy)][None, :]
    if rules.has_tie_break(ally) != rules.has_tie_break(enemy):
        ally_wins_ties = rules.has_tie_break(ally)
    elif ally.stars != enemy.stars:
        ally_wins_ties = ally.stars < enemy.stars
    else:
        ally_wins_ties = scratch.turn
    return np.where(ally_attack != enemy_attack, ally_attack > enemy_attack, ally_wins_ties)


def _apply_to(current: np.ndarray, bonus: int, borne, increase: bool) -> np.ndarray:
    """`apply_capacity_lvl_2._apply_to`, vectorisé : une borne max pour une hausse, min pour une baisse."""
    if borne is not None and borne != -1:
        if increase:
            return np.where(current < borne, np.minimum(borne, current + bonus), current)
        return np.where(current > borne, np.maximum(borne, current + bonus), current)
    return current + bonus
