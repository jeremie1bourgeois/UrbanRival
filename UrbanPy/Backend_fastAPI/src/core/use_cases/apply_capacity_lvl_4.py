"""
Niveau 4 : effets persistants (poison / toxine / heal / regen / dope / repair / consume / combust).
À la fin d'un round où les deux joueurs sont en vie :
  1. les effets déjà actifs agissent (« à la fin de chaque round suivant » leur activation) ;
  2. les capacités persistantes restantes (leur condition de fin de round a été validée au niveau 3) sont
     enregistrées sur le joueur affecté : cible ally -> propriétaire, enemy -> adversaire ; le multiplicateur
     est résolu à l'activation ; un effet remplace l'effet de même sorte (poison et toxine se cumulent,
     heal et regen aussi, dope et repair aussi) ;
  3. toxine, regen, dope et consume « agissent immédiatement à la fin du round dans lequel ils ont été joués »
     (glossaire officiel 51, 52 ; repair et combust : utilisateur) : les effets de ces sortes enregistrés ce round
     agissent aussitôt.
Repair et combust portent sur la vie ET les pillz ; un Annul Modif. Vie / Pillz suspend un effet attribut par
attribut, donc seule la moitié annulée saute (combats réels 1211702 et 1211922).
Un poison peut amener un joueur à 0 vie : la fin de partie est constatée par check_end.
"""
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.effect import PersistentEffect
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.domain.journal import label, note
from src.core.use_cases.multipliers import multiplier

IMMEDIATE_KINDS = ("toxine", "regen", "dope", "repair", "consume", "combust")
_LOSS_KINDS = ("poison", "toxine", "consume", "combust")           # les autres sortes font gagner
_CAUSED_BY_OPPONENT = ("poison", "toxine", "consume", "combust")   # posés sur un joueur par son adversaire

# Attributs touchés par chaque sorte : repair verse la vie et les pillz, combust prend les deux (combat réel 1211702)
_STATS_OF_KIND = {"poison": ("life",), "toxine": ("life",), "heal": ("life",), "regen": ("life",),
                  "dope": ("pillz",), "consume": ("pillz",), "repair": ("life", "pillz"), "combust": ("life", "pillz")}


def _suspended(effect: PersistentEffect, player_card: Card, opp_card: Card) -> tuple:
    """
    Attributs de l'effet suspendus ce round par un Annul Modif. Vie / Pillz Adv. visant la carte qui l'a posé
    (glossaire 56). Attribut par attribut : un Annul Vie contre un Repair verse les pillz, pas la vie
    (combat réel 1211922).
    """
    author = opp_card if effect.kind in _CAUSED_BY_OPPONENT else player_card
    return tuple(stat for stat in _STATS_OF_KIND[effect.kind] if stat in author.cancelled_modifs)


def apply_capacity_lvl_4(game: Game, card1: Card, card2: Card) -> None:
    sides = ((card1, card2, game.ally, game.enemy), (card2, card1, game.enemy, game.ally))
    for card, opp_card, own, opp in sides:
        side = _side(game, own)
        for effect in own.effect_list:
            suspended = _suspended(effect, card, opp_card)
            if suspended == _STATS_OF_KIND[effect.kind]:
                note(None, "persistant", f"{effect.kind} {effect.value} sur {side} suspendu ce round (Annul)")
            else:
                if suspended:
                    note(None, "persistant", f"{effect.kind} {effect.value} sur {side} : {' et '.join(suspended)} suspendu ce round (Annul)")
                _tick(own, effect, side, suspended)
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
                bound = "" if capacity.borne in (None, -1) else (f" (min {capacity.borne})" if kind in _LOSS_KINDS else f" (max {capacity.borne})")
                note(card, "persistant", f"{card.name} : {label(capacity)} → {kind} {value}{bound} sur {_side(game, player)}")
                suspended = tuple(stat for stat in _STATS_OF_KIND[kind] if stat in card.cancelled_modifs)
                if kind in IMMEDIATE_KINDS and suspended != _STATS_OF_KIND[kind]:
                    _tick(player, effect, _side(game, player), suspended)
            setattr(card, slot, None)


def register_persistent_effect(player: Player, effect: PersistentEffect) -> None:
    """Ajoute l'effet en remplaçant l'effet de même sorte s'il existe."""
    player.effect_list = [existing for existing in player.effect_list if existing.kind != effect.kind]
    player.effect_list.append(effect)


def _side(game: Game, player: Player) -> str:
    return "l'allié" if player is game.ally else "l'ennemi"


def tick_persistent_effects(player: Player, skip=None) -> None:
    for effect in player.effect_list:
        if skip is None or not skip(effect):
            _tick(player, effect)


def _tick(player: Player, effect: PersistentEffect, side: str = None, suspended: tuple = ()) -> None:
    life, pillz = player.life, player.pillz
    _apply_tick(player, effect, suspended)
    if side is not None:
        changes = [f"vie de {side} {life} → {player.life}"] * (player.life != life) + [f"pillz de {side} {pillz} → {player.pillz}"] * (player.pillz != pillz)
        note(None, "persistant", f"{effect.kind} {effect.value} → " + (", ".join(changes) if changes else f"rien (borne {effect.borne} atteinte)"))


def _apply_tick(player: Player, effect: PersistentEffect, suspended: tuple = ()) -> None:
    """Applique l'effet à chacun de ses attributs, sauf ceux suspendus ce round par un Annul."""
    unbounded = effect.borne is None or effect.borne == -1
    for attr in _STATS_OF_KIND[effect.kind]:
        if attr in suspended:
            continue
        current = getattr(player, attr)
        if effect.kind in _LOSS_KINDS:
            floor = 0 if unbounded else effect.borne
            if current > floor:
                setattr(player, attr, max(floor, current - effect.value))
        elif unbounded:
            setattr(player, attr, current + effect.value)
        elif current < effect.borne:
            setattr(player, attr, min(effect.borne, current + effect.value))
