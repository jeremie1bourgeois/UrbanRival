"""
Niveau 4 : effets persistants (poison / toxine / heal / regen / dope / repair / consume / combust).
À la fin d'un round où les deux joueurs sont en vie :
  1. les effets déjà actifs agissent (« à la fin de chaque round suivant » leur activation) ;
  2. les capacités persistantes restantes (leur condition de fin de round a été validée au niveau 3) sont
     enregistrées sur le joueur affecté : cible ally -> propriétaire, enemy -> adversaire ; le multiplicateur
     est résolu à l'activation ; un effet remplace l'effet de même sorte (poison et toxine se cumulent,
     heal et regen aussi, dope et repair aussi) ;
  3. toxine, regen, dope et consume « agissent immédiatement à la fin du round dans lequel ils ont été joués »
     (glossaire officiel 51, 52) : les effets de ces sortes enregistrés ce round agissent aussitôt.
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
_PILLZ_LOSS = ("consume",)
IMMEDIATE_KINDS = ("toxine", "regen", "dope", "consume")
_LIFE_LOSS_AND_PILLZ_LOSS = ("combust",)


_STAT_OF_KIND = {"poison": "life", "toxine": "life", "heal": "life", "regen": "life",
                 "dope": "pillz", "repair": "pillz", "consume": "pillz", "combust": "life"}
_CAUSED_BY_OPPONENT = ("poison", "toxine", "consume", "combust")   # posés sur un joueur par son adversaire


def _suspended(effect: PersistentEffect, player_card: Card, opp_card: Card) -> bool:
    """Un Annul Modif Vie/Pillz Adv. suspend pour le round les effets persistants de la carte annulée (glossaire 56)."""
    author = opp_card if effect.kind in _CAUSED_BY_OPPONENT else player_card
    return _STAT_OF_KIND[effect.kind] in author.cancelled_modifs


def apply_capacity_lvl_4(game: Game, card1: Card, card2: Card) -> None:
    sides = ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally))
    for card, opp_card, own, opp in sides:
        tick_persistent_effects(own, skip=lambda effect: _suspended(effect, card, opp_card))
    for card, opp_card, own, opp in sides:
        for slot in FIGHT_SLOTS:
            capacity = getattr(card, slot)
            if capacity is None:
                continue
            kind = next((type_ for type_ in capacity.types if type_ in PersistentEffect.KINDS), None)
            if kind is None:
                continue
            value = capacity.value * multiplier(capacity.how, game, own, opp, card, opp_card)
            affected = {"enemy": [opp], "ally": [own], "both": [own, opp]}[capacity.target]
            for player in affected:
                effect = PersistentEffect(kind, value, capacity.borne)
                register_persistent_effect(player, effect)
                if kind in IMMEDIATE_KINDS and _STAT_OF_KIND[kind] not in card.cancelled_modifs:
                    _tick(player, effect)
            setattr(card, slot, None)


def register_persistent_effect(player: Player, effect: PersistentEffect) -> None:
    """Ajoute l'effet en remplaçant l'effet de même sorte s'il existe."""
    player.effect_list = [existing for existing in player.effect_list if existing.kind != effect.kind]
    player.effect_list.append(effect)


def _lose(player: Player, attr: str, value: int, floor: int) -> None:
    current = getattr(player, attr)
    if current > floor:
        setattr(player, attr, max(floor, current - value))


def tick_persistent_effects(player: Player, skip=None) -> None:
    for effect in player.effect_list:
        if skip is None or not skip(effect):
            _tick(player, effect)


def _tick(player: Player, effect: PersistentEffect) -> None:
    unbounded = effect.borne is None or effect.borne == -1
    floor = 0 if unbounded else effect.borne
    if effect.kind in _LIFE_LOSS:
        _lose(player, "life", effect.value, floor)
    elif effect.kind in _PILLZ_LOSS:
        _lose(player, "pillz", effect.value, floor)
    elif effect.kind in _LIFE_LOSS_AND_PILLZ_LOSS:
        _lose(player, "life", effect.value, floor)
        _lose(player, "pillz", effect.value, floor)
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
