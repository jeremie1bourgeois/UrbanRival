"""
Niveau 1 : capacités « méta » qui agissent sur les autres capacités ou sur les valeurs imprimées, avant tout
modificateur de stats. Quatre phases, puis les capacités méta sont consommées (None) :
  1. Copy: Opp. Ability / Bonus  — l'emplacement copieur devient une copie de l'emplacement adverse
  2. Protection: Ability / Bonus puis Stop Opp. Ability / Bonus — résolution simultanée (voir _stopped_kinds) ;
     une capacité « Stop: X » s'active si son emplacement est stoppé, et reste inerte sinon
  3. Copy / Exchange de power et damage — sur les valeurs imprimées
  4. Cancel Opp. X Modif. (retire X des modifications adverses, quelle que soit leur cible) et
     Protection: X (retire X des modifications adverses qui ciblent ma carte)
Règles retenues là où Urban Rivals est ambigu : les Stops s'appliquent tous en même temps (SoA vs SoA :
les deux abilities tombent ; SoA vs SoB : l'un perd son ability, l'autre son bonus) ; une protection tombe
si l'adversaire stoppe l'emplacement où elle se trouve, sauf si une autre protection non tombée la couvre ;
en cas de cycle (les deux protections face aux deux stops), les stops gagnent.
"""
import copy
from typing import Optional, Set

from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS

META_HOWS = {"stop", "copy", "Protection", "cancel", "exchange", "impose"}
SLOT_OF_KIND = {"ability": "ability_fight", "bonus": "bonus_fight"}
KIND_OF_SLOT = {"ability_fight": "ability", "bonus_fight": "bonus"}
STAT_TYPES = ("power", "damage", "attack")


def apply_capacity_lvl_1(card1: Card, card2: Card) -> None:
    _apply_copies(card1, card2)
    _apply_stops(card1, card2)
    _apply_value_copies_and_exchanges(card1, card2)
    _apply_cancels(card1, card2)
    _apply_stat_protections(card1, card2)
    _consume_meta_capacities(card1, card2)


# --- Utilitaires ------------------------------------------------------------------------------

def _is(capacity: Optional[Capacity], how: str) -> bool:
    return capacity is not None and capacity.how == how


def _kind_targeted(capacity: Optional[Capacity]) -> Optional[str]:
    """« ability » ou « bonus » si la capacité méta vise un emplacement, sinon None (ex. Copy: Opp. Power)."""
    if capacity is None:
        return None
    return next((kind for kind in ("ability", "bonus") if kind in capacity.types), None)


def _pairs(card1: Card, card2: Card):
    return ((card1, card2), (card2, card1))


# --- Phase 1 : Copy: Opp. Ability / Bonus -----------------------------------------------------

def _apply_copies(card1: Card, card2: Card) -> None:
    planned = []
    for own, opp in _pairs(card1, card2):
        for slot in SLOT_OF_KIND.values():
            capacity = getattr(own, slot)
            kind = _kind_targeted(capacity) if _is(capacity, "copy") else None
            if kind is None:
                continue
            source = getattr(opp, SLOT_OF_KIND[kind])
            copied = None if _is(source, "copy") and _kind_targeted(source) else copy.deepcopy(source)
            planned.append((own, slot, copied))
    for own, slot, copied in planned:     # simultané : les deux copies lisent l'état d'origine
        setattr(own, slot, copied)


# --- Phase 2 : Protection: Ability / Bonus et Stop Opp. Ability / Bonus -----------------------

def _slots_targeting(card: Card, how: str) -> dict:
    """(« ability » / « bonus ») visé -> emplacements de `card` qui portent une capacité méta `how` le visant."""
    slots = {}
    for slot in SLOT_OF_KIND.values():
        capacity = getattr(card, slot)
        if _is(capacity, how) and _kind_targeted(capacity):
            slots.setdefault(_kind_targeted(capacity), []).append(slot)
    return slots


def _stopped_slots(card1: Card, card2: Card) -> Set[tuple]:
    """
    Emplacements (carte, « ability » / « bonus ») stoppés, résolus « en chaîne » (règle officielle, support UR art. 91 :
    « check that nothing is blocking it and […] that nothing is blocking the Ability/Bonus block ») : un Stop stoppé ne
    stoppe rien, une Protection stoppée ne protège rien. Point fixe sur les emplacements sûrement actifs / sûrement
    stoppés ; ce qui reste indéterminé (cycle, ex. SoA contre SoA) est stoppé : les Stops gagnent.
    """
    cards = {id(card1): card1, id(card2): card2}
    opp_of = {id(card1): card2, id(card2): card1}
    stops = {id(c): _slots_targeting(c, "stop") for c in cards.values()}
    protections = {id(c): _slots_targeting(c, "Protection") for c in cards.values()}
    every = {(id(c), kind) for c in cards.values() for kind in ("ability", "bonus")}
    active, stopped = set(), set()

    def state(slot_key):                 # slot_key = (id carte, emplacement)
        return (slot_key[0], KIND_OF_SLOT[slot_key[1]])

    changed = True
    while changed:
        changed = False
        for key in every - active - stopped:
            card_id, kind = key
            attackers = [(id(opp_of[card_id]), slot) for slot in stops[id(opp_of[card_id])].get(kind, [])]
            shields = [(card_id, slot) for slot in protections[card_id].get(kind, [])]
            if all(state(a) in stopped for a in attackers) or any(state(s) in active for s in shields):
                active.add(key); changed = True
            elif any(state(a) in active for a in attackers) and all(state(s) in stopped for s in shields):
                stopped.add(key); changed = True
    return every - active                # indéterminé -> stoppé


def _apply_stops(card1: Card, card2: Card) -> None:
    stopped = _stopped_slots(card1, card2)
    for card in (card1, card2):
        for kind, slot in SLOT_OF_KIND.items():
            capacity = getattr(card, slot)
            if capacity is None:
                continue
            if (id(card), kind) in stopped:
                if "stop" in capacity.effect_conditions:      # « Stop: X » : X s'active justement parce qu'on la stoppe
                    capacity.effect_conditions.remove("stop")
                else:
                    setattr(card, slot, None)
            elif "stop" in capacity.effect_conditions:        # pas stoppée : « Stop: X » reste inerte
                setattr(card, slot, None)


# --- Phase 3 : Copy / Exchange / Impose de power et damage ---------------------------------------------

def _apply_value_copies_and_exchanges(card1: Card, card2: Card) -> None:
    for own, opp in _pairs(card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(own, slot)
            if capacity is None or capacity.how not in ("copy", "exchange", "impose"):
                continue
            for stat in ("power", "damage"):
                if stat not in capacity.types:
                    continue
                if capacity.how == "impose":                       # l'adversaire prend ma valeur imprimée
                    setattr(opp, f"{stat}_fight", getattr(own, stat))
                    continue
                setattr(own, f"{stat}_fight", getattr(opp, stat))
                if capacity.how == "exchange":
                    setattr(opp, f"{stat}_fight", getattr(own, stat))


# --- Phase 4 : Cancel Opp. X Modif. et Protection: X ------------------------------------------

def _strip_types(card: Card, types: Set[str], only_targeting_opponent: bool) -> None:
    """Retire `types` des capacités d'effet de `card` ; une capacité sans type restant disparaît."""
    for slot in FIGHT_SLOTS:
        capacity = getattr(card, slot)
        if capacity is None or capacity.how in META_HOWS:
            continue
        if only_targeting_opponent and capacity.target != "enemy":
            continue
        capacity.types = [type_ for type_ in capacity.types if type_ not in types]
        if not capacity.types:
            setattr(card, slot, None)


# Les effets persistants sont des modificateurs de vie / de pillz : un Cancel Opp. Life (Pillz) Modif. les annule aussi
# (règle officielle : « poison, toxin, regen and heal abilities will be deactivated for the round »).
PERSISTENT_TYPES_OF_STAT = {"life": {"poison", "toxine", "heal", "regen"}, "pillz": {"dope"}}


def _apply_cancels(card1: Card, card2: Card) -> None:
    for own, opp in _pairs(card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(own, slot)
            if _is(capacity, "cancel"):
                types = set(capacity.types)
                for stat in capacity.types:
                    types |= PERSISTENT_TYPES_OF_STAT.get(stat, set())
                _strip_types(opp, types, only_targeting_opponent=False)


def _apply_stat_protections(card1: Card, card2: Card) -> None:
    for own, opp in _pairs(card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(own, slot)
            if _is(capacity, "Protection"):
                protected = set(capacity.types) & set(STAT_TYPES)
                if protected:
                    _strip_types(opp, protected, only_targeting_opponent=True)


# --- Consommation -----------------------------------------------------------------------------

def _consume_meta_capacities(card1: Card, card2: Card) -> None:
    for card in (card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(card, slot)
            if capacity is not None and capacity.how in META_HOWS:
                setattr(card, slot, None)
