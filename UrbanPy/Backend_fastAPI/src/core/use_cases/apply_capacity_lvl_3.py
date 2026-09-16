from src.core.domain.player import Player
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.game import Game
from src.core.use_cases.multipliers import multiplier

# Types de capacité du niveau 3 -> attribut du joueur modifié
_TYPE_MAP = {
    "life": "life",
    "pillz": "pillz",
}


def apply_capacity_lvl_3(game: Game, card1: Card, card2: Card) -> None:
    """
    Effets de fin de round sur la vie / les pillz des joueurs (les deux joueurs sont encore en vie).
    Chaque capacité restante est filtrée par sa condition de fin de round puis appliquée une seule fois.
    """
    for card, opp_card, own, opp in ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally)):
        for slot in FIGHT_SLOTS:
            capacity = getattr(card, slot)
            if capacity is None:
                continue
            capacity = check_capacity_condition_lvl_3(capacity, card.win)
            if capacity is not None and "reanimate" in capacity.types:
                capacity = None   # Reanimate n'agit que sur un KO (apply_reanimate), jamais en fin de round normale
            for apply in (apply_target_ally_effects, apply_target_both_effects, apply_target_enemy_effects):
                if capacity is None:
                    break
                capacity = apply(game, own, opp, capacity, card, opp_card)
            setattr(card, slot, capacity)


def apply_reanimate(game: Game, card1: Card, card2: Card) -> None:
    """Reanimate : le joueur tombé à 0 vie récupère X vies si la carte qu'il vient de jouer porte l'effet."""
    if game.ally.life <= 0:
        _reanimate(game, game.ally, game.enemy, card1, card2)
    if game.enemy.life <= 0:
        _reanimate(game, game.enemy, game.ally, card2, card1)


def _reanimate(game: Game, own: Player, opp: Player, card: Card, opp_card: Card) -> None:
    for slot in FIGHT_SLOTS:
        capacity = getattr(card, slot)
        if capacity is not None and "reanimate" in capacity.types:
            own.life += capacity.value * multiplier(capacity.how, game, own, opp, card, opp_card)
            setattr(card, slot, None)


def check_capacity_condition_lvl_3(capacity: Capacity, has_won: bool) -> Capacity:
    """Filtre une capacité selon l'issue du round : sans condition = seulement en cas de victoire."""
    if capacity.effect_conditions == []:
        return capacity if has_won else None
    elif "backlash" in capacity.effect_conditions:
        if has_won:
            capacity.target = "ally"
            capacity.effect_conditions = []
            return capacity
        return None
    elif "defeat" in capacity.effect_conditions:
        if not has_won:
            capacity.effect_conditions = []
            return capacity
        return None
    elif "victory_defeat" in capacity.effect_conditions:
        capacity.effect_conditions = []
        return capacity
    else:
        raise ValueError(f"Invalid effect_conditions (check_capacity_condition_lvl_3): {capacity.effect_conditions}")


def _apply_to(player: Player, attrs: list, bonus: int, borne: int) -> None:
    for attr in attrs:
        current_value = getattr(player, attr)
        if borne is not None and borne != -1:
            if bonus > 0 and current_value < borne:      # augmentation avec borne max
                setattr(player, attr, min(borne, current_value + bonus))
            elif bonus < 0 and current_value > borne:    # diminution avec borne min
                setattr(player, attr, max(borne, current_value + bonus))
        else:
            setattr(player, attr, current_value + bonus)


def _apply_targeted(target: str, players: list, game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    """Applique la capacité aux joueurs donnés si sa cible est `target` ; renvoie None une fois consommée."""
    if capacity.target != target:
        return capacity
    attrs = [_TYPE_MAP[type_] for type_ in capacity.types if type_ in _TYPE_MAP]
    if not attrs:
        return capacity
    bonus = capacity.value * multiplier(capacity.how, game, player1, player2, card1, card2)
    for player in players:
        _apply_to(player, attrs, bonus, capacity.borne)
    return None


def apply_target_ally_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    return _apply_targeted("ally", [player1], game, player1, player2, capacity, card1, card2)


def apply_target_enemy_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    return _apply_targeted("enemy", [player2], game, player1, player2, capacity, card1, card2)


def apply_target_both_effects(game: Game, player1: Player, player2: Player, capacity: Capacity, card1: Card, card2: Card) -> Capacity:
    return _apply_targeted("both", [player1, player2], game, player1, player2, capacity, card1, card2)
