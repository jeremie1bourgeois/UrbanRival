"""
Niveau 1 : capacités « méta » qui agissent sur les autres capacités ou sur les valeurs imprimées, avant tout
modificateur de stats. Quatre phases, puis les capacités méta sont consommées (None) :
  1. Copy: Opp. Ability / Bonus  — l'emplacement copieur devient une copie de l'emplacement adverse
  2. Protection: Ability / Bonus puis Stop Opp. Ability / Bonus — résolution « en chaîne » (voir _stopped_slots) ;
     une capacité « Stop: X » s'active si son emplacement est stoppé, et reste inerte sinon
  3. Copy / Exchange / Impose de power et damage — sur les valeurs imprimées
  4. Cancel Opp. X Modif. (retire X des modifications adverses, quelle que soit leur cible ; Life / Pillz suspendent
     aussi les effets persistants adverses pour le round — glossaire officiel 56) et Protection: X (retire X des modifications adverses qui ciblent ma carte ;
     « Cards » protège les deux cartes)
Règle officielle des Stops (support UR, art. 91) : un Stop stoppé ne stoppe rien, une Protection stoppée ne protège
rien ; les cycles (SoA contre SoA, deux Protections face à deux Stops) ne sont pas tranchés par la source : les Stops
gagnent. Tune Out survit à la consommation : process_round le lit pour résoudre le round aux pillz.
"""
import copy
from typing import Optional, Set

from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.journal import STAT_LABELS, label, note, stat_change

META_HOWS = {"stop", "copy", "Protection", "cancel", "exchange", "impose", "tune_out", "tie_break"}
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


_KIND_LABELS = {"ability": "pouvoir", "bonus": "bonus"}


def _of(card: Card) -> str:
    """« d'Amelia » / « de Bhudd »."""
    return ("d'" if card.name[:1].lower() in "aeiouyéè" else "de ") + card.name


def _description(card: Card, kind: str) -> str:
    return card.ability_description if kind == "ability" else card.bonus_description


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
            if copied is not None:
                copied.label = f"copie du {_KIND_LABELS[kind]} {_of(opp)} « {_description(opp, kind)} »"
                note(own, "copie", f"{own.name} : {label(capacity)} copie le {_KIND_LABELS[kind]} {_of(opp)} « {_description(opp, kind)} »")
            else:
                note(own, "copie", f"{own.name} : {label(capacity)} ne copie rien ({_KIND_LABELS[kind]} {_of(opp)} absent ou lui-même une copie)")
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
    for card, opp in _pairs(card1, card2):
        for kind, slot in SLOT_OF_KIND.items():
            capacity = getattr(card, slot)
            if capacity is None:
                continue
            if (id(card), kind) in stopped:
                stoppers = [getattr(opp, s) for s in _slots_targeting(opp, "stop").get(kind, [])
                            if (id(opp), KIND_OF_SLOT[s]) not in stopped]
                by = f"stoppé par {opp.name} ({label(stoppers[0])})" if stoppers else "stoppé (cycle de Stops)"
                if "stop" in capacity.effect_conditions:      # « Stop: X » : X s'active justement parce qu'on la stoppe
                    capacity.effect_conditions.remove("stop")
                    note(card, "stop", f"{card.name} : {label(capacity)} s'active ({by})")
                else:
                    note(card, "stop", f"{card.name} : {label(capacity)} {by}")
                    setattr(card, slot, None)
            elif "stop" in capacity.effect_conditions:        # pas stoppée : « Stop: X » reste inerte
                note(card, "stop", f"{card.name} : {label(capacity)} inactif (pas de Stop adverse)")
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
                own_before, opp_before = getattr(own, f"{stat}_fight"), getattr(opp, f"{stat}_fight")
                if capacity.how == "impose":                       # l'adversaire prend ma valeur imprimée
                    setattr(opp, f"{stat}_fight", getattr(own, stat))
                    note(own, "impose", f"{own.name} : {label(capacity)} → {stat_change(stat, _of(opp), opp_before, getattr(opp, f'{stat}_fight'))}")
                    continue
                setattr(own, f"{stat}_fight", getattr(opp, stat))
                changes = [stat_change(stat, _of(own), own_before, getattr(own, f"{stat}_fight"))]
                if capacity.how == "exchange":
                    setattr(opp, f"{stat}_fight", getattr(own, stat))
                    changes.append(stat_change(stat, _of(opp), opp_before, getattr(opp, f"{stat}_fight")))
                note(own, capacity.how, f"{own.name} : {label(capacity)} → " + ", ".join(changes))


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


def _apply_cancels(card1: Card, card2: Card) -> None:
    for own, opp in _pairs(card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(own, slot)
            if _is(capacity, "cancel"):
                types = set(capacity.types)
                stats = " et ".join(STAT_LABELS.get(type_, type_) for type_ in capacity.types)
                note(own, "annule", f"{own.name} : {label(capacity)} annule les modifications de {stats} {_of(opp)}")
                _strip_types(opp, types, only_targeting_opponent=False)
                opp.cancelled_modifs |= types & {"life", "pillz"}   # les persistants adverses ne tiquent pas ce round (glossaire 56)
                if capacity.target == "both":                  # « Cancel Players X Mod. » (Leaders) : les deux côtés
                    _strip_types(own, types, only_targeting_opponent=False)
                    own.cancelled_modifs |= types & {"life", "pillz"}


def _apply_stat_protections(card1: Card, card2: Card) -> None:
    for own, opp in _pairs(card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(own, slot)
            if _is(capacity, "Protection"):
                protected = set(capacity.types) & set(STAT_TYPES)
                if protected:
                    stats = " et ".join(STAT_LABELS[type_] for type_ in capacity.types if type_ in protected)
                    possessive = "sa" if len(protected) == 1 and "damage" not in protected else "ses"
                    note(own, "protection", f"{own.name} : {label(capacity)} protège {possessive} {stats}")
                    _strip_types(opp, protected, only_targeting_opponent=True)
                    if capacity.target == "both":                  # « Protection: Cards X » protège aussi la carte adverse
                        _strip_types(own, protected, only_targeting_opponent=True)


# --- Consommation -----------------------------------------------------------------------------

def _consume_meta_capacities(card1: Card, card2: Card) -> None:
    for card in (card1, card2):
        for slot in FIGHT_SLOTS:
            capacity = getattr(card, slot)
            if capacity is not None and capacity.how in META_HOWS and capacity.how not in ("tune_out", "tie_break"):   # lus par process_round
                setattr(card, slot, None)
