"""
Niveau 4 : effets persistants (poison / toxine / heal / regen / dope / repair / consume / combust / mindwipe).
À la fin d'un round où les deux joueurs sont en vie :
  1. les effets déjà actifs agissent (« à la fin de chaque round suivant » leur activation) ;
  2. les capacités persistantes restantes (leur condition de fin de round a été validée au niveau 3) sont
     enregistrées sur le joueur affecté : cible ally -> propriétaire, enemy -> adversaire ; le multiplicateur
     est résolu à l'activation ; un effet remplace l'effet de même sorte (poison et toxine se cumulent,
     heal et regen aussi, dope et repair aussi) ;
  3. toxine, regen, dope et consume « agissent immédiatement à la fin du round dans lequel ils ont été joués »
     (glossaire officiel 51, 52), mindwipe (combat réel 1211279) et repair (« gagne X points de Vie ET Pillz, maximum Y »,
     combat réel 1211702) aussi : les effets de ces sortes enregistrés ce round agissent aussitôt.
Un Annul Modif. Vie / Pillz suspend l'effet attribut par attribut : sur un effet vie + pillz (combust, mindwipe, repair),
seule la moitié annulée saute (combat réel 1211922 : Repair sous Annul Modif. Vie verse le pillz, pas la vie).
Un poison peut amener un joueur à 0 vie : la fin de partie est constatée par check_end.
"""
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.effect import PersistentEffect
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.domain.journal import label, note
from src.core.use_cases.multipliers import multiplier

LOSING_KINDS = ("poison", "toxine", "consume", "combust", "mindwipe")   # les autres (heal, regen, dope, repair) font gagner
IMMEDIATE_KINDS = ("toxine", "regen", "dope", "consume", "mindwipe", "repair")


_STATS_OF_KIND = {"poison": ("life",), "toxine": ("life",), "heal": ("life",), "regen": ("life",), "dope": ("pillz",),
                  "consume": ("pillz",), "repair": ("life", "pillz"), "combust": ("life", "pillz"), "mindwipe": ("life", "pillz")}
_CAUSED_BY_OPPONENT = ("poison", "toxine", "consume", "combust", "mindwipe")   # posés sur un joueur par son adversaire


def _suspended(effect: PersistentEffect, player_card: Card, opp_card: Card) -> tuple:
    """Attributs de l'effet suspendus ce round par un Annul Modif Vie/Pillz Adv. visant la carte auteur (glossaire 56)."""
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
                _tick(own, effect, side, skip=suspended)
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
                bound = "" if capacity.borne in (None, -1) else (f" (min {capacity.borne})" if kind in LOSING_KINDS else f" (max {capacity.borne})")
                note(card, "persistant", f"{card.name} : {label(capacity)} → {kind} {value}{bound} sur {_side(game, player)}")
                if kind in IMMEDIATE_KINDS:
                    skip = tuple(stat for stat in _STATS_OF_KIND[kind] if stat in card.cancelled_modifs)
                    if skip != _STATS_OF_KIND[kind]:
                        _tick(player, effect, _side(game, player), skip=skip)
            setattr(card, slot, None)


def register_persistent_effect(player: Player, effect: PersistentEffect) -> None:
    """Ajoute l'effet en remplaçant l'effet de même sorte s'il existe."""
    player.effect_list = [existing for existing in player.effect_list if existing.kind != effect.kind]
    player.effect_list.append(effect)


def _lose(player: Player, attr: str, value: int, floor: int) -> None:
    current = getattr(player, attr)
    if current > floor:
        setattr(player, attr, max(floor, current - value))


def _side(game: Game, player: Player) -> str:
    return "l'allié" if player is game.ally else "l'ennemi"


def tick_persistent_effects(player: Player, skip=None) -> None:
    for effect in player.effect_list:
        if skip is None or not skip(effect):
            _tick(player, effect)


def _tick(player: Player, effect: PersistentEffect, side: str = None, skip: tuple = ()) -> None:
    life, pillz = player.life, player.pillz
    _apply_tick(player, effect, skip)
    if side is not None:
        changes = [f"vie de {side} {life} → {player.life}"] * (player.life != life) + [f"pillz de {side} {pillz} → {player.pillz}"] * (player.pillz != pillz)
        note(None, "persistant", f"{effect.kind} {effect.value} → " + (", ".join(changes) if changes else f"rien (borne {effect.borne} atteinte)"))


def _apply_tick(player: Player, effect: PersistentEffect, skip: tuple = ()) -> None:
    """Applique l'effet à ses attributs (sauf ceux de `skip`, suspendus par un Annul ce round)."""
    unbounded = effect.borne is None or effect.borne == -1
    floor = 0 if unbounded else effect.borne
    ceiling = None if unbounded else effect.borne
    losing = effect.kind in LOSING_KINDS
    for attr in _STATS_OF_KIND[effect.kind]:
        if attr in skip:
            continue
        if losing:
            _lose(player, attr, effect.value, floor)
        else:
            _gain(player, attr, effect.value, ceiling)


def _gain(player: Player, attr: str, value: int, ceiling) -> None:
    current = getattr(player, attr)
    if ceiling is None:
        setattr(player, attr, current + value)
    elif current < ceiling:
        setattr(player, attr, min(ceiling, current + value))
