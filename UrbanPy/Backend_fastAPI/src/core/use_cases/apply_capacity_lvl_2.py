"""
Niveau 2 : modificateurs de power / damage / attack des cartes en combat.
Appelé en deux passes par process_round : power et damage avant le calcul de l'attaque (puissance x pillz),
attack après — sinon un « -X Opp Attack, Min Y » s'appliquerait à une attaque encore nulle.
Une capacité est consommée (None) quand tous ses types de niveau 2 ont été appliqués.
"""
from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.game import Game
from src.core.use_cases.multipliers import multiplier

# Type de capacité -> attribut de la carte modifié
_ATTR_MAP = {
    "power": "power_fight",
    "damage": "damage_fight",
    "attack": "attack",
}
ALL_STATS = tuple(_ATTR_MAP)


def apply_capacity_lvl_2(game: Game, card1: Card, card2: Card, stats=ALL_STATS) -> None:
    """Applique les modificateurs des stats `stats` : cible ally, puis both, puis enemy, pour chaque emplacement."""
    for apply in (apply_target_ally_effects, apply_target_both_effects, apply_target_enemy_effects):
        for card, opp_card, own, opp in ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally)):
            for slot in FIGHT_SLOTS:
                capacity = getattr(card, slot)
                if capacity is not None:
                    setattr(card, slot, apply(game, own, opp, capacity, card, opp_card, stats))


def _apply_to(card: Card, attrs: list, bonus: int, borne: int, increase: bool) -> None:
    for attr in attrs:
        current_value = getattr(card, attr)
        if borne is not None and borne != -1:
            if increase and current_value < borne:          # augmentation avec borne max
                setattr(card, attr, min(borne, current_value + bonus))
            elif not increase and current_value > borne:    # diminution avec borne min
                setattr(card, attr, max(borne, current_value + bonus))
        else:
            setattr(card, attr, current_value + bonus)


def _apply_targeted(target: str, cards: list, game: Game, player1: Player, player2: Player, capacity: Capacity,
                    card1: Card, card2: Card, stats) -> Capacity:
    """Applique la capacité aux cartes données si sa cible est `target` ; consommée quand ses types niveau 2 sont épuisés."""
    if capacity.target != target:
        return capacity
    applied = [type_ for type_ in capacity.types if type_ in stats]
    if not applied:
        return capacity
    bonus = capacity.value * multiplier(capacity.how, game, player1, player2, card1, card2)
    attrs = [_ATTR_MAP[type_] for type_ in applied]
    for card in cards:
        _apply_to(card, attrs, bonus, capacity.borne, increase=capacity.value > 0)
    capacity.types = [type_ for type_ in capacity.types if type_ not in applied]
    return capacity if capacity.types else None


def apply_target_ally_effects(game, player1, player2, capacity, card1, card2, stats=ALL_STATS) -> Capacity:
    return _apply_targeted("ally", [card1], game, player1, player2, capacity, card1, card2, stats)


def apply_target_enemy_effects(game, player1, player2, capacity, card1, card2, stats=ALL_STATS) -> Capacity:
    return _apply_targeted("enemy", [card2], game, player1, player2, capacity, card1, card2, stats)


def apply_target_both_effects(game, player1, player2, capacity, card1, card2, stats=ALL_STATS) -> Capacity:
    return _apply_targeted("both", [card1, card2], game, player1, player2, capacity, card1, card2, stats)
