"""
Niveau 4 : effets persistants (poison / toxine / heal / regen / dope / repair).
À la fin d'un round où les deux joueurs sont en vie :
  1. les effets déjà actifs agissent (« à la fin de chaque round suivant » leur activation) ;
  2. les capacités persistantes restantes (leur condition de fin de round a été validée au niveau 3) sont
     enregistrées sur le joueur affecté : cible ally -> propriétaire, enemy -> adversaire ; le multiplicateur
     est résolu à l'activation ; un effet remplace l'effet de même sorte (poison et toxine se cumulent,
     heal et regen aussi, dope et repair aussi).
Un poison peut amener un joueur à 0 vie : la fin de partie est constatée par check_end.
"""
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.effect import PersistentEffect
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.use_cases.multipliers import multiplier

_LIFE_LOSS = ("poison", "toxine")
_LIFE_GAIN = ("heal", "regen")
_PILLZ_GAIN = ("dope", "repair")


def apply_capacity_lvl_4(game: Game, card1: Card, card2: Card) -> None:
    tick_persistent_effects(game.ally)
    tick_persistent_effects(game.enemy)
    for card, opp_card, own, opp in ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally)):
        for slot in FIGHT_SLOTS:
            capacity = getattr(card, slot)
            if capacity is None:
                continue
            kind = next((type_ for type_ in capacity.types if type_ in PersistentEffect.KINDS), None)
            if kind is None:
                continue
            value = capacity.value * multiplier(capacity.how, game, own, opp, card, opp_card)
            affected = opp if capacity.target == "enemy" else own
            register_persistent_effect(affected, PersistentEffect(kind, value, capacity.borne))
            setattr(card, slot, None)


def register_persistent_effect(player: Player, effect: PersistentEffect) -> None:
    """Ajoute l'effet en remplaçant l'effet de même sorte s'il existe."""
    player.effect_list = [existing for existing in player.effect_list if existing.kind != effect.kind]
    player.effect_list.append(effect)


def tick_persistent_effects(player: Player) -> None:
    for effect in player.effect_list:
        unbounded = effect.borne is None or effect.borne == -1
        if effect.kind in _LIFE_LOSS:
            floor = 0 if unbounded else effect.borne
            if player.life > floor:
                player.life = max(floor, player.life - effect.value)
        elif effect.kind in _LIFE_GAIN:
            if unbounded:
                player.life += effect.value
            elif player.life < effect.borne:
                player.life = min(effect.borne, player.life + effect.value)
        elif effect.kind in _PILLZ_GAIN:
            if unbounded:
                player.pillz += effect.value
            elif player.pillz < effect.borne:
                player.pillz = min(effect.borne, player.pillz + effect.value)
