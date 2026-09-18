"""
Contrat du moteur pur : la représentation compacte (entiers, booléens, aucun texte) d'une partie, que tout moteur —
le moteur Python de référence comme un moteur compilé — doit savoir jouer à l'identique. Deux moitiés :
  - le deck, immuable pendant la partie : 8 cartes compilées, dont les capacités sont des indices dans un vocabulaire
    figé et des masques de bits ;
  - l'état, qui change à chaque round : round, premier joueur, vies, pillz, cartes jouées, effets persistants (dans
    l'ordre d'activation : le niveau 4 les applique dans cet ordre), dernier round (lu par Revenge / Confidence / After).
Un état contient exactement ce que process_round lit, rien de plus : test_engine_contract rejoue des parties depuis la
forme compacte et exige le même résultat qu'avec les objets d'origine.
Le vocabulaire est figé ici (et non dérivé du parseur) pour que ses indices soient stables : un moteur compilé les
reprend tels quels. Ajouter une valeur = l'ajouter en fin de tuple.
"""
from dataclasses import dataclass
from typing import NamedTuple, Optional, Tuple

from src.core.domain.capacity import Capacity
from src.core.domain.card import Card
from src.core.domain.effect import PersistentEffect
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.domain.round import Round

HOWS = ("", "Protection", "brawl", "cancel", "copy", "counter_attack", "degrowth", "equalizer", "exchange", "growth",
        "impose", "limitless", "nb_dam_opp", "nb_damage", "nb_life_left", "nb_life_lost", "nb_pillz_left",
        "nb_pillz_lost", "nb_pow_opp", "stop", "support", "tie_break", "tune_out")
TYPES = ("ability", "attack", "bonus", "combust", "consume", "counter_attack", "damage", "dope", "heal", "infiltrated",
         "ko", "life", "limitless", "pillz", "poison", "power", "reanimate", "recover", "regen", "repair", "tie_break",
         "toxine", "tune_out")
CONDITIONS = ("after", "asymmetry", "backlash", "bet", "confidence", "courage", "defeat", "disunion", "infiltrated",
              "killshot", "perfect", "reprisal", "revenge", "stop", "symmetry", "team", "unison", "versus",
              "victory_defeat")
CLAN_CONDITIONS = ("versus", "after", "infiltrated")   # conditions paramétrées par une liste de clans
TARGETS = ("ally", "enemy", "both")
CLANS = ("All Stars", "Bangers", "Berzerk", "Cosmohnuts", "Dominion", "Fang Pi Clang", "Freaks", "Frozn", "GHEIST",
         "GhosTown", "Hive", "Huracan", "Jungo", "Junkz", "Komboka", "La Junta", "Leader", "Montana", "Nightmare",
         "Oblivion", "Oculus", "Paradox", "Piranas", "Pussycats", "Raptors", "Rescue", "Riots", "Roots", "Sakrohm",
         "Sentinel", "Skeelz", "Tolvack", "Ulu Watu", "Uppers", "Vortex", "Zenith")
EFFECT_KINDS = PersistentEffect.KINDS


@dataclass(frozen=True)
class CompiledCapacity:
    how: int              # indice dans HOWS
    target: int           # indice dans TARGETS
    types: int            # masque de bits sur TYPES
    value: int
    borne: int            # -1 = sans borne
    conditions: int       # masque de bits sur CONDITIONS
    bet_over: int = 0     # « Bet > N » : N, si le bit « bet » est levé et bet_under vaut 0
    bet_under: int = 0    # « Bet < N » : N (jamais 0 : une mise n'est pas négative)
    clans: int = 0        # masque de bits sur CLANS de la condition versus / after / infiltrated (une seule par capacité)


@dataclass(frozen=True)
class CompiledCard:
    name: str             # identité, pour lire un corpus ; le moteur ne la lit pas
    stars: int
    clan: int             # indice dans CLANS
    power: int
    damage: int
    ability: Optional[CompiledCapacity]
    bonus: Optional[CompiledCapacity]


@dataclass(frozen=True)
class Deck:
    ally: Tuple[CompiledCard, ...]
    enemy: Tuple[CompiledCard, ...]


@dataclass(frozen=True)
class PlayerState:
    life: int
    pillz: int
    played: Tuple[bool, ...]                    # une entrée par carte de la main
    effects: Tuple[Tuple[int, int, int], ...]   # (indice dans EFFECT_KINDS, value, borne), dans l'ordre d'activation


@dataclass(frozen=True)
class State:
    nb_turn: int
    ally_first: bool                            # Game.turn : l'allié joue en premier ce round
    ally: PlayerState
    enemy: PlayerState
    last_round: Optional[Tuple[int, int, bool]] # (carte alliée, carte ennemie, l'allié a gagné) ; None au round 1


class Action(NamedTuple):
    card: int         # indice dans la main
    pillz: int        # pillz_fight : 1 + mise (la pillz gratuite comprise)
    fury: bool


# --- Vocabulaire <-> masques -------------------------------------------------------------------

def _mask(vocabulary: tuple, names) -> int:
    mask = 0
    for name in names:
        mask |= 1 << vocabulary.index(name)
    return mask


def _names(vocabulary: tuple, mask: int) -> list:
    return [name for index, name in enumerate(vocabulary) if mask >> index & 1]


# --- Capacité ---------------------------------------------------------------------------------

def compile_capacity(capacity: Optional[Capacity]) -> Optional[CompiledCapacity]:
    if capacity is None:
        return None
    conditions, bet_over, bet_under, clans = 0, 0, 0, 0
    for condition in capacity.effect_conditions:
        name, _, parameter = condition.partition(":")
        if name.startswith("bet"):                       # « bet>N », « bet<N » (forme historique « bet N » = « bet>N »)
            name, parameter = "bet", condition[3:].strip()
            if parameter.startswith("<"):
                bet_under = int(parameter[1:])
            else:
                bet_over = int(parameter.lstrip(">").strip())
        elif parameter:
            clans = _mask(CLANS, parameter.split("|"))
        conditions |= 1 << CONDITIONS.index(name)
    return CompiledCapacity(how=HOWS.index(capacity.how), target=TARGETS.index(capacity.target),
                            types=_mask(TYPES, capacity.types), value=capacity.value, borne=capacity.borne,
                            conditions=conditions, bet_over=bet_over, bet_under=bet_under, clans=clans)


def capacity_from_compiled(compiled: Optional[CompiledCapacity]) -> Optional[Capacity]:
    if compiled is None:
        return None
    conditions = []
    for name in _names(CONDITIONS, compiled.conditions):
        if name == "bet":
            conditions.append(f"bet<{compiled.bet_under}" if compiled.bet_under else f"bet>{compiled.bet_over}")
        elif name in CLAN_CONDITIONS:
            conditions.append(name + ":" + "|".join(_names(CLANS, compiled.clans)))
        else:
            conditions.append(name)
    return Capacity(target=TARGETS[compiled.target], types=_names(TYPES, compiled.types), value=compiled.value,
                    borne=compiled.borne, how=HOWS[compiled.how], effect_conditions=conditions)


# --- Carte ------------------------------------------------------------------------------------

def compile_card(card: Card) -> CompiledCard:
    return CompiledCard(name=card.name, stars=card.stars, clan=CLANS.index(card.faction), power=card.power,
                        damage=card.damage, ability=compile_capacity(card.ability), bonus=compile_capacity(card.bonus))


def card_from_compiled(compiled: CompiledCard, played: bool) -> Card:
    """Carte du moteur Python bâtie sur la forme compilée seule (sans relire les données officielles)."""
    card = Card.__new__(Card)
    card.name = compiled.name
    card.faction = CLANS[compiled.clan]
    card.starOff = 0
    card.stars = compiled.stars
    card.power = compiled.power
    card.damage = compiled.damage
    card.ability = capacity_from_compiled(compiled.ability)
    card.bonus = capacity_from_compiled(compiled.bonus)
    card.image = card.clan_image = ""
    card.ability_description = card.bonus_description = ""
    card.power_fight = card.damage_fight = card.pillz_fight = card.attack = 0
    card.ability_fight = card.bonus_fight = card.leader_fight = None
    card.fury = card.win = False
    card.played = played
    card.cancelled_modifs = set()
    return card


# --- Partie <-> (deck, état) ------------------------------------------------------------------

def deck_from_game(game: Game) -> Deck:
    return Deck(ally=tuple(compile_card(card) for card in game.ally.cards),
                enemy=tuple(compile_card(card) for card in game.enemy.cards))


def _player_state(player: Player) -> PlayerState:
    return PlayerState(life=player.life, pillz=player.pillz, played=tuple(card.played for card in player.cards),
                       effects=tuple((EFFECT_KINDS.index(effect.kind), effect.value, effect.borne)
                                     for effect in player.effect_list))


def state_from_game(game: Game) -> State:
    last = game.history[-1] if game.history else None
    return State(nb_turn=game.nb_turn, ally_first=game.turn, ally=_player_state(game.ally),
                 enemy=_player_state(game.enemy),
                 last_round=None if last is None else (last.ally.card_index, last.enemy.card_index, last.ally.win))


def _player(name: str, cards: Tuple[CompiledCard, ...], state: PlayerState) -> Player:
    return Player(name=name, life=state.life, pillz=state.pillz,
                  cards=[card_from_compiled(card, played) for card, played in zip(cards, state.played)],
                  effect_list=[PersistentEffect(EFFECT_KINDS[kind], value, borne) for kind, value, borne in state.effects])


def game_from_state(deck: Deck, state: State) -> Game:
    """Partie jouable par process_round ; l'historique est réduit au dernier round, seul lu par le moteur."""
    history = []
    if state.last_round is not None:
        ally_index, enemy_index, ally_won = state.last_round
        last = Round()
        last.ally.card_index, last.ally.win = ally_index, ally_won
        last.enemy.card_index, last.enemy.win = enemy_index, not ally_won
        history.append(last)
    return Game(nb_turn=state.nb_turn, turn=state.ally_first, ally=_player("ally", deck.ally, state.ally),
                enemy=_player("enemy", deck.enemy, state.enemy), history=history)


# --- JSON (l'écriture est dataclasses.asdict ; les tuples y deviennent des listes) ------------

def _capacity_from_dict(fields: Optional[dict]) -> Optional[CompiledCapacity]:
    return None if fields is None else CompiledCapacity(**fields)


def _card_from_dict(fields: dict) -> CompiledCard:
    return CompiledCard(**{**fields, "ability": _capacity_from_dict(fields["ability"]),
                           "bonus": _capacity_from_dict(fields["bonus"])})


def deck_from_dict(fields: dict) -> Deck:
    return Deck(ally=tuple(map(_card_from_dict, fields["ally"])), enemy=tuple(map(_card_from_dict, fields["enemy"])))


def _player_state_from_dict(fields: dict) -> PlayerState:
    return PlayerState(life=fields["life"], pillz=fields["pillz"], played=tuple(fields["played"]),
                       effects=tuple(tuple(effect) for effect in fields["effects"]))


def state_from_dict(fields: dict) -> State:
    last_round = fields["last_round"]
    return State(nb_turn=fields["nb_turn"], ally_first=fields["ally_first"],
                 ally=_player_state_from_dict(fields["ally"]), enemy=_player_state_from_dict(fields["enemy"]),
                 last_round=None if last_round is None else tuple(last_round))
