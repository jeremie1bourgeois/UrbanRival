"""
Scénarios combinatoires du moteur : des situations construites une à une — cartes synthétiques à valeurs contrôlées,
capacités prises dans les descriptions officielles — pour exercer chaque capacité, chaque interaction méta, chaque
condition et chaque effet persistant dans des contextes choisis, là où le corpus aléatoire ne garantit rien.
Chaque famille est un générateur déterministe (sans graine, sauf « aleatoire ») de Scenario : deck compilé, état,
actions du round. corpus.py les joue avec le moteur de référence et enregistre l'état suivant et l'issue du round ;
un moteur compilé doit reproduire chaque entrée.
Le moteur applique les effets de l'allié avant ceux de l'ennemi et, avec des planchers, l'ordre compte : les familles
où cela peut jouer enregistrent aussi le scénario miroir (camps échangés, premier joueur inversé), pour qu'un port
reproduise les deux orientations.
"""
import random
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import product
from typing import Dict, Iterator, List, Optional, Tuple

from src.adapters.repositories.card_repository import _official_cards, all_capacity_descriptions
from src.core.domain.capacity import Capacity
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.engine.contract import (CLANS, EFFECT_KINDS, Action, CompiledCard, Deck, PlayerState, State,
                                      compile_capacity, deck_from_game, state_from_game)
from src.core.engine.hands import random_hand
from src.core.engine.reference import legal_actions, step, terminal
from src.core.parsing.capacity_parser import parse_capacity
from src.core.use_cases.apply_capacity_lvl_1 import META_HOWS


@dataclass(frozen=True)
class Scenario:
    label: str
    deck: Deck
    state: State
    ally_action: Action
    enemy_action: Action

    def mirrored(self) -> "Scenario":
        """Le même round vu de l'autre camp : decks, états et actions échangés, premier joueur inversé."""
        last = self.state.last_round
        state = State(nb_turn=self.state.nb_turn, ally_first=not self.state.ally_first, ally=self.state.enemy,
                      enemy=self.state.ally, last_round=None if last is None else (last[1], last[0], not last[2]))
        return Scenario(self.label + "/miroir", Deck(ally=self.deck.enemy, enemy=self.deck.ally), state,
                        self.enemy_action, self.ally_action)


# --- Capacités ----------------------------------------------------------------------------------

def capacity(text: str) -> Capacity:
    parsed = parse_capacity(text)
    if not parsed.supported or parsed.capacity is None:
        raise ValueError(f"capacité non jouable : {text!r} ({parsed.reason})")
    return parsed.capacity


@lru_cache(maxsize=1)
def distinct_capacities() -> Tuple[Tuple[str, Capacity], ...]:
    """Une description par capacité compilée distincte (la première par ordre alphabétique), toutes gérées."""
    seen, result = set(), []
    for text in sorted(all_capacity_descriptions()):
        parsed = parse_capacity(text)
        if not parsed.supported or parsed.capacity is None:
            continue
        key = compile_capacity(parsed.capacity)
        if key not in seen:
            seen.add(key)
            result.append((text, parsed.capacity))
    return tuple(result)


def _condition_names(cap: Capacity) -> set:
    return {condition.partition(":")[0] for condition in cap.effect_conditions}


def _clans_of(cap: Capacity, prefix: str) -> List[str]:
    for condition in cap.effect_conditions:
        if condition.startswith(prefix + ":"):
            return condition.split(":", 1)[1].split("|")
    return []


def _shape(cap: Capacity) -> tuple:
    """Forme d'une capacité, valeur mise à part : ce qui détermine son comportement face aux capacités méta."""
    return (cap.how, cap.target, tuple(sorted(cap.types)), tuple(sorted(_condition_names(cap))),
            (cap.value > 0) - (cap.value < 0), cap.borne != -1)


@lru_cache(maxsize=1)
def distinct_shapes() -> Tuple[Tuple[str, Capacity], ...]:
    seen, result = set(), []
    for text, cap in distinct_capacities():
        if _shape(cap) not in seen:
            seen.add(_shape(cap))
            result.append((text, cap))
    return tuple(result)


@lru_cache(maxsize=1)
def clan_bonus_texts() -> Dict[str, str]:
    """Texte du bonus de chaque clan, lu sur sa première carte officielle (« Cancel Leader » pour les Leaders)."""
    texts = {}
    for card_data in _official_cards().values():
        texts.setdefault(card_data.get("faction", ""), card_data.get("bonus", "").strip())
    return texts


# --- Cartes et mains synthétiques ---------------------------------------------------------------

ALLY_CLAN, ENEMY_CLAN, OTHER_CLAN, THIRD_CLAN = "Bangers", "Junkz", "Freaks", "Montana"
ALLY_POWER, ALLY_DAMAGE, ENEMY_POWER, ENEMY_DAMAGE = 7, 4, 6, 5
STATS = ("power", "damage", "attack")
SOLO_ENEMY_POWER, SOLO_ENEMY_DAMAGE = 8, 6   # famille solo : assez haut pour que « Min 6 » / « Min 5 » réduisent encore
PLAYED_INDEX, ENEMY_INDEX = 1, 2     # la carte porteuse est en position 1, l'adversaire joue sa position 2


def card(name: str, power: int, damage: int, stars: int = 3, clan: str = ALLY_CLAN,
         ability: Optional[Capacity] = None, bonus: Optional[Capacity] = None) -> CompiledCard:
    return CompiledCard(name=name, stars=stars, clan=CLANS.index(clan), power=power, damage=damage,
                        ability=compile_capacity(ability), bonus=compile_capacity(bonus))


def hand(prefix: str, power: int, damage: int, clan: str, ability: Optional[Capacity] = None,
         bonus: Optional[Capacity] = None, ability_index: int = PLAYED_INDEX, stars: int = 3,
         clans: Optional[Tuple[str, ...]] = None) -> Tuple[CompiledCard, ...]:
    """Quatre cartes identiques (noms distincts : le bonus de clan compte les personnages) ; l'ability sur une seule."""
    return tuple(card(f"{prefix}{index}", power, damage, stars, clans[index] if clans else clan,
                      ability if index == ability_index else None, bonus) for index in range(4))


def ally_hand(ability=None, bonus=None, clans=None, stars=3, power=ALLY_POWER, damage=ALLY_DAMAGE) -> Tuple[CompiledCard, ...]:
    return hand("A", power, damage, ALLY_CLAN, ability, bonus, stars=stars, clans=clans)


def enemy_hand(ability=None, bonus=None, clans=None, stars=3, ability_index=ENEMY_INDEX,
               power=ENEMY_POWER, damage=ENEMY_DAMAGE) -> Tuple[CompiledCard, ...]:
    return hand("E", power, damage, ENEMY_CLAN, ability, bonus, ability_index, stars, clans)


def _clan_not_in(listed: List[str]) -> str:
    preferred = (ENEMY_CLAN, OTHER_CLAN, THIRD_CLAN) + tuple(clan for clan in CLANS if clan not in ("Leader", "Oculus"))
    return next(clan for clan in preferred if clan not in listed)


# --- Contextes ----------------------------------------------------------------------------------

ROUND_STOCKS = {1: (12, 12, 12, 12), 2: (10, 9, 8, 10), 3: (9, 7, 10, 6), 4: (7, 4, 9, 3)}   # vie, pillz allié ; vie, pillz ennemi
PLAY_ORDER = (0, 3, 2, 1)   # ordre dans lequel les cartes ont été jouées aux rounds précédents (hors carte de ce round)
WIN_BET, LOSE_BET = 6, 1    # pillz_fight : 7 × 6 = 42 contre 6 ou 8 × 1, décisif malgré les modificateurs


@dataclass(frozen=True)
class Context:
    name: str
    nb_turn: int = 1
    ally_first: bool = True
    ally_won_last: Optional[bool] = None    # issue du round précédent (None au round 1)
    ally_index: int = PLAYED_INDEX
    enemy_index: int = ENEMY_INDEX
    ally_pillz: int = LOSE_BET               # pillz_fight (pillz gratuite comprise)
    enemy_pillz: int = LOSE_BET
    ally_fury: bool = False
    enemy_fury: bool = False
    stocks: Optional[Tuple[int, int, int, int]] = None   # vie, pillz allié ; vie, pillz ennemi (défaut : ROUND_STOCKS)
    ally_effects: Tuple[Tuple[int, int, int], ...] = ()
    enemy_effects: Tuple[Tuple[int, int, int], ...] = ()


def _played_before(nb_turn: int, index: int) -> List[int]:
    return [i for i in PLAY_ORDER if i != index][:nb_turn - 1]


def label(*parts: str) -> str:
    """Identifiant « famille/…/contexte » ; le « / » des descriptions (« +1 Pow./ Life Lost ») devient « ∕ »."""
    return "/".join(str(part).replace("/", "∕") for part in parts)


def build(label_prefix: str, ally: Tuple[CompiledCard, ...], enemy: Tuple[CompiledCard, ...], ctx: Context) -> Scenario:
    life_a, pillz_a, life_e, pillz_e = ctx.stocks or ROUND_STOCKS[ctx.nb_turn]
    ally_played, enemy_played = _played_before(ctx.nb_turn, ctx.ally_index), _played_before(ctx.nb_turn, ctx.enemy_index)
    last = None if ctx.nb_turn == 1 else (ally_played[-1], enemy_played[-1], bool(ctx.ally_won_last))
    state = State(nb_turn=ctx.nb_turn, ally_first=ctx.ally_first,
                  ally=PlayerState(life_a, pillz_a, tuple(i in ally_played for i in range(4)), ctx.ally_effects),
                  enemy=PlayerState(life_e, pillz_e, tuple(i in enemy_played for i in range(4)), ctx.enemy_effects),
                  last_round=last)
    return Scenario(f"{label_prefix}/{ctx.name}", Deck(ally=ally, enemy=enemy), state,
                    Action(ctx.ally_index, ctx.ally_pillz, ctx.ally_fury), Action(ctx.enemy_index, ctx.enemy_pillz, ctx.enemy_fury))


def _outcome_context(name: str, nb_turn: int, ally_first: bool, won_last, wins: bool, **overrides) -> Context:
    _, pillz_a, _, pillz_e = ROUND_STOCKS[nb_turn]
    bets = {"ally_pillz": min(pillz_a + 1, WIN_BET), "enemy_pillz": LOSE_BET} if wins else \
           {"ally_pillz": LOSE_BET, "enemy_pillz": min(pillz_e + 1, WIN_BET)}
    return Context(name, nb_turn, ally_first, won_last, **{**bets, **overrides})


ROUNDS = ((1, None), (2, False), (3, True), (4, False))   # (round, l'allié a gagné le round précédent)


def base_contexts(firsts=(True, False), rounds=ROUNDS) -> List[Context]:
    """Victoire / défaite × premier / second × rounds 1 à 4 (historique perdu, gagné, perdu)."""
    return [_outcome_context(f"r{nb_turn}-{'premier' if ally_first else 'second'}-{'gagne' if wins else 'perd'}",
                             nb_turn, ally_first, won_last, wins)
            for nb_turn, won_last in rounds for ally_first in firsts for wins in (True, False)]


WIN_R1 = _outcome_context("r1-premier-gagne", 1, True, None, True)
LOSE_R1 = _outcome_context("r1-premier-perd", 1, True, None, False)


# --- Famille « solo » : chaque capacité, seule, en pouvoir puis en bonus ------------------------

PERFECT_BETS = {ENEMY_POWER: (2, 2), SOLO_ENEMY_POWER: (3, 2)}   # 14 contre 12 (écart 2), 21 contre 16 (écart 5) : < 7, victoire


def _condition_contexts(cut: Capacity, enemy_power: int = SOLO_ENEMY_POWER) -> List[Context]:
    names = _condition_names(cut)
    extras = []
    if names & {"symmetry", "asymmetry"}:
        extras += [replace(WIN_R1, name="r1-premier-gagne-symetrique", enemy_index=PLAYED_INDEX),
                   replace(LOSE_R1, name="r1-premier-perd-symetrique", enemy_index=PLAYED_INDEX)]
    for condition in cut.effect_conditions:
        if condition.startswith("bet"):                      # « bet>N » : N ne remplit pas, N + 1 remplit ; « bet<N » : l'inverse
            threshold = int(condition[4:])
            for bet in (threshold, threshold + 1 if condition[3] == ">" else threshold - 1):
                if 1 <= bet <= 13:
                    extras.append(Context(f"r1-premier-mise-{bet}", ally_pillz=bet))
    if "killshot" in names:
        extras.append(Context("r1-premier-gagne-sans-killshot", ally_pillz=3, enemy_pillz=2))     # 21 < 2 × 12 ou 2 × 16
    if "perfect" in names:
        ally_bet, enemy_bet = PERFECT_BETS[enemy_power]
        extras.append(Context("r1-premier-gagne-perfect", ally_pillz=ally_bet, enemy_pillz=enemy_bet))
    return extras


def _solo_enemy(clans=None) -> Tuple[CompiledCard, ...]:
    return enemy_hand(clans=clans, power=SOLO_ENEMY_POWER, damage=SOLO_ENEMY_DAMAGE)


def _hand_variants(cut: Capacity, placement: str):
    """(nom, main alliée, clans de la main ennemie ou None) : la base, plus les compositions qui remplissent les conditions de main."""
    ability, bonus = (cut, None) if placement == "pouvoir" else (None, cut)
    yield "base", ally_hand(ability, bonus), None
    names = _condition_names(cut)
    if names & {"unison", "disunion"}:
        yield "main-mixte", ally_hand(ability, bonus, clans=(ALLY_CLAN, ALLY_CLAN, ALLY_CLAN, OTHER_CLAN)), None
    versus = _clans_of(cut, "versus")
    if versus:
        yield "versus-present", ally_hand(ability, bonus), (ENEMY_CLAN, ENEMY_CLAN, ENEMY_CLAN, versus[0])
        yield "versus-absent", ally_hand(ability, bonus), (_clan_not_in(versus),) * 4
    after = _clans_of(cut, "after")
    if after:   # toute la main du clan : la carte du round précédent en est, et le bonus reste actif
        yield "after-present", ally_hand(ability, bonus, clans=(after[0],) * 4), None
    infiltrated = _clans_of(cut, "infiltrated")
    if infiltrated:   # hors Oculus, le clan retenu est celui de la carte : une main entière du clan listé
        yield "clan-liste", ally_hand(ability, bonus, clans=(infiltrated[0],) * 4), None
    if cut.target == "ally" and cut.value > 0 and cut.borne != -1 and set(cut.types) & set(STATS):
        yield "carte-faible", ally_hand(ability, bonus, power=4, damage=2), None   # le maximum n'est pas déjà atteint


def _variant_contexts(cut: Capacity, variant: str) -> List[Context]:
    contexts = base_contexts()
    if variant == "base":
        return contexts + _condition_contexts(cut)
    if variant == "after-present":
        return [ctx for ctx in contexts if ctx.nb_turn > 1]
    return contexts


def solo_scenarios() -> Iterator[Scenario]:
    """Chaque capacité distincte, en pouvoir puis en bonus ; une orientation sur deux est le miroir."""
    count = 0
    for text, cut in distinct_capacities():
        for placement in ("pouvoir", "bonus"):
            for variant, ally, enemy_clans in _hand_variants(cut, placement):
                for ctx in _variant_contexts(cut, variant):
                    scenario = build(label("solo", placement, text, variant), ally, _solo_enemy(enemy_clans), ctx)
                    yield scenario if count % 2 == 0 else scenario.mirrored()
                    count += 1


# --- Famille « interactions » : chaque forme de capacité face aux capacités méta adverses --------

# (nom, texte, dépend de l'emplacement) : les sondes qui visent un emplacement sont posées en pouvoir puis en bonus
PROBES = (
    ("stop-pouvoir", "Stop Opp. Ability", True), ("stop-bonus", "Stop Opp. Bonus", True),
    ("protection-pouvoir", "Protection: Ability", True), ("protection-bonus", "Protection: Bonus", True),
    ("copie-pouvoir", "Copy: Opp. Ability", True), ("copie-bonus", "Copy: Opp. Bonus", True),
    ("annule-puissance", "Cancel Opp. Power Modif.", False), ("annule-degats", "Cancel Opp. Damage Modif.", False),
    ("annule-attaque", "Cancel Opp. Attack Modif.", False), ("annule-vie", "Cancel Opp. Life Modif.", False),
    ("annule-pillz", "Cancel Opp. Pillz Modif.", False), ("annule-puissance-degats", "Cancel Opp. Power And Damage Modif.", False),
    ("protege-puissance", "Protection: Power", False), ("protege-degats", "Protection: Damage", False),
    ("protege-attaque", "Protection: Attack", False), ("protege-puissance-degats", "Protection: Power And Damage", False),
    ("protege-cartes", "Protection: Cards Power And Damage", False),
    ("echange-puissance", "Power Exchange", False), ("echange-degats", "Damage Exchange", False),
    ("echange-puissance-degats", "Power And Damage Exchange", False),
    ("impose-puissance", "Power Impose", False), ("impose-degats", "Damage Impose", False),
    ("copie-puissance", "Copy: Opp. Power", False), ("copie-degats", "Copy: Opp. Damage", False),
    ("copie-puissance-degats", "Copy: Power And Damage Opp.", False),
    ("tune-out", "Tune Out", False),
    ("stop-conditionne", "Stop: Power +3", False), ("stop-conditionne-vie", "Stop: -3 Opp. Life, Min 0", False),
    ("reducteur", "-2 Opp Power, Min 1", True), ("cartes-degats", "-2 Cards Damage, Min 1", True),
    ("temoin-damage", "-2 Opp Damage, Min 1", False), ("temoin-attack", "-5 Opp Attack, Min 2", False),
    ("temoin-life", "-2 Opp. Life Min 2", False), ("temoin-pillz", "-1 Opp Pillz. Min 1", False),
)
# Témoins d'effet par stat : ce qu'un Stop / Copy / Protection / Cancel rend visible une fois actif
WITNESSES = {"power": "-2 Opp Power, Min 1", "damage": "-2 Opp Damage, Min 1", "attack": "-5 Opp Attack, Min 2",
             "life": "-2 Opp. Life Min 2", "pillz": "-1 Opp Pillz. Min 1"}
_PROBE_BY_NAME = {name: text for name, text, _ in PROBES}
_PROBE_BY_NAME.update({f"temoin-{stat}": text for stat, text in WITNESSES.items()})
_STAT_PROBES = {"power": ("annule-puissance", "protege-puissance"), "damage": ("annule-degats", "protege-degats"),
                "attack": ("annule-attaque", "protege-attaque"), "life": ("annule-vie",), "pillz": ("annule-pillz",),
                "poison": ("annule-vie",), "toxine": ("annule-vie",), "heal": ("annule-vie",), "regen": ("annule-vie",),
                "dope": ("annule-pillz",), "repair": ("annule-pillz",), "consume": ("annule-pillz",),
                "combust": ("annule-vie", "annule-pillz"), "recover": ("annule-pillz",), "reanimate": ("annule-vie",)}


def _is_meta(cap: Capacity) -> bool:
    return cap.how in META_HOWS or bool(_condition_names(cap) & {"stop", "killshot", "perfect"}) or "ko" in cap.types


ROUND_START_CONDITIONS = {"courage", "reprisal", "revenge", "confidence", "symmetry", "asymmetry", "unison", "disunion",
                          "versus", "after", "infiltrated", "bet"}


def _has_round_start_condition(cap: Capacity) -> bool:
    return any(name.startswith("bet") or name in ROUND_START_CONDITIONS for name in _condition_names(cap))


def _relevant_probes(cut: Capacity, placement: str) -> List[Tuple[str, str, bool]]:
    """Pour une capacité d'effet : ce qui peut la stopper, la copier, l'annuler ou la protéger, plus un témoin."""
    names = ["stop-pouvoir", "copie-pouvoir"] if placement == "pouvoir" else ["stop-bonus", "copie-bonus"]
    names += ["tune-out", "reducteur"]
    for type_ in cut.types:
        names += [name for name in _STAT_PROBES.get(type_, ()) if name not in names]
    return [(name, _PROBE_BY_NAME[name], False) for name in names]


def _interaction(placement: str, text: str, cut: Capacity, probe_name: str, probe_slot: str, ctx: Context,
                 variant: str = "base", ally: Optional[Tuple[CompiledCard, ...]] = None, enemy_clans=None) -> Scenario:
    probe = capacity(_PROBE_BY_NAME[probe_name])
    if ally is None:
        ally = ally_hand(cut, None) if placement == "pouvoir" else ally_hand(None, cut)
    enemy = enemy_hand(ability=probe, clans=enemy_clans) if probe_slot == "pouvoir" else enemy_hand(bonus=probe, clans=enemy_clans)
    return build(label("interactions", placement, text, variant, f"{probe_name}-en-{probe_slot}"), ally, enemy, ctx)


# Formes à condition de début de round : round 1 (premier / second × gagne / perd), round 2 perdu et round 3 gagné
CONDITIONED_CONTEXTS = base_contexts(rounds=ROUNDS[:1]) + base_contexts(rounds=ROUNDS[1:3])[::2]


def _slot_targeted(cut: Capacity) -> Optional[str]:
    """« pouvoir » / « bonus » si la capacité méta vise un emplacement (Stop, Copy, Protection), sinon None."""
    kind = next((kind for kind in ("ability", "bonus") if kind in cut.types), None)
    return {"ability": "pouvoir", "bonus": "bonus"}.get(kind)


def _protected_slot(cut: Capacity) -> Optional[str]:
    """Emplacement allié qu'une Protection d'emplacement protège : il lui faut un témoin pour être visible."""
    return _slot_targeted(cut) if cut.how == "Protection" else None


def _conditioned_probes(cut: Capacity, placement: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    (sonde adverse, son emplacement, emplacement d'un témoin allié ou None) qui rendent visible une capacité à
    condition une fois active : un Stop / Copy d'emplacement face à un témoin adverse dans cet emplacement, une
    Protection d'emplacement avec un témoin allié dans cet emplacement face au Stop adverse, une Protection / un
    Cancel de stat face au témoin adverse de cette stat ; une capacité d'effet face au Stop et au Copy de son emplacement.
    """
    slot = _slot_targeted(cut)
    if cut.how in ("stop", "copy") and slot:
        return [("temoin-power", slot, None)]
    if cut.how == "Protection" and slot:
        return [(f"stop-{slot}", "pouvoir", slot)]
    if cut.how in ("Protection", "cancel"):
        return [(f"temoin-{stat}", "pouvoir", None) for stat in cut.types if stat in WITNESSES]
    return [(f"stop-{placement}", "pouvoir", None), (f"copie-{placement}", "pouvoir", None)]


def _with_witness(ally: Tuple[CompiledCard, ...], slot: Optional[str]) -> Tuple[CompiledCard, ...]:
    if slot is None:
        return ally
    witness = capacity(WITNESSES["power"])
    return tuple(replace(card, ability=compile_capacity(witness)) if slot == "pouvoir" and index == PLAYED_INDEX
                 else replace(card, bonus=compile_capacity(witness)) if slot == "bonus" else card
                 for index, card in enumerate(ally))


def interactions_scenarios() -> Iterator[Scenario]:
    """
    Formes méta sans condition de début de round × toutes les sondes, dans les deux emplacements et les deux
    orientations ; formes d'effet sans condition × sondes utiles ; formes à condition × la sonde qui les rend
    visibles (_conditioned_probes), dans les mains et contextes qui remplissent (ou non) la condition — c'est aussi
    le copieur qui réévalue la condition copiée.
    """
    for text, cut in distinct_shapes():
        if _has_round_start_condition(cut):
            for placement in ("pouvoir", "bonus"):
                for variant, ally, enemy_clans in _hand_variants(cut, placement):
                    contexts = CONDITIONED_CONTEXTS + (_condition_contexts(cut, ENEMY_POWER) if variant == "base" else [])
                    for (probe_name, probe_slot, witness_slot), ctx in product(_conditioned_probes(cut, placement), contexts):
                        if variant == "after-present" and ctx.nb_turn == 1:
                            continue
                        if witness_slot == placement:      # le témoin prendrait la place de la capacité testée
                            continue
                        yield _interaction(placement, text, cut, probe_name, probe_slot, ctx, variant, _with_witness(ally, witness_slot), enemy_clans)
            continue
        meta = _is_meta(cut)
        for placement in ("pouvoir", "bonus"):
            if _protected_slot(cut) == placement:          # le témoin protégé prendrait la place de la capacité testée
                continue
            ally = _with_witness(ally_hand(cut, None) if placement == "pouvoir" else ally_hand(None, cut), _protected_slot(cut))
            contexts = (_condition_contexts(cut, ENEMY_POWER)[-1], LOSE_R1) if "perfect" in cut.effect_conditions else (WIN_R1, LOSE_R1)
            for probe_name, _, slot_dependent in (PROBES if meta else _relevant_probes(cut, placement)):
                for probe_slot in (("pouvoir", "bonus") if slot_dependent else ("pouvoir",)):
                    for ctx in contexts:
                        scenario = _interaction(placement, text, cut, probe_name, probe_slot, ctx, ally=ally)
                        yield scenario
                        if meta:
                            yield scenario.mirrored()


# --- Famille « planchers » : ordre des réductions (REGLES 3.6 bis) ------------------------------

def _reducers(stat: str) -> Dict[Tuple[int, int], str]:
    """(valeur, Min) -> description, pour les « -X Opp <stat>, Min Y » sans condition ni multiplicateur."""
    shapes = {}
    for text, cap in distinct_capacities():
        if cap.how == "" and cap.target == "enemy" and cap.types == [stat] and cap.value < 0 and not cap.effect_conditions:
            shapes.setdefault((cap.value, cap.borne), text)
    return dict(sorted(shapes.items()))


def _both_reducers(stat: str) -> List[Tuple[str, Capacity]]:
    return [(text, cap) for text, cap in distinct_capacities()
            if cap.target == "both" and cap.how in ("", "support") and cap.types == [stat] and cap.value < 0 and not cap.effect_conditions]


FLOORS_CONTEXT = Context("r1", ally_pillz=3, enemy_pillz=4)   # attaques 21 et 32 : les planchers d'attaque jouent


def floors_scenarios() -> Iterator[Scenario]:
    enemy = enemy_hand(power=8, damage=8)
    for stat in STATS:
        reducers = _reducers(stat)
        for (bonus_text, ability_text) in product(reducers.values(), repeat=2):    # bonus + pouvoir sur la même carte
            yield build(label("planchers", stat, f"bonus {bonus_text} + pouvoir {ability_text}"),
                        ally_hand(capacity(ability_text), capacity(bonus_text)), enemy, FLOORS_CONTEXT)
        for team_text in ("Team: -1 Opp. Power, Min 0", "Team: -2 Opp. Damage, Min 2", "Team: -2 Opp. Damage, Min 3"):
            if stat not in capacity(team_text).types:
                continue
            for bonus_text in reducers.values():                                      # bonus + Leader
                leader = card("L", 5, 4, clan="Leader", ability=capacity(team_text))
                ally = ally_hand(None, capacity(bonus_text))[:3] + (leader,)
                yield build(label("planchers", stat, f"bonus {bonus_text} + {team_text}"), ally, enemy, FLOORS_CONTEXT)
        for both_text, both_cap in _both_reducers(stat):                              # « Cards » allié contre réducteur ennemi
            for reducer_text in reducers.values():
                scenario = build(label("planchers", stat, f"cartes {both_text} contre {reducer_text}"),
                                 ally_hand(both_cap), enemy_hand(ability=capacity(reducer_text), power=8, damage=8), FLOORS_CONTEXT)
                yield scenario
                yield scenario.mirrored()
            for other_text, other_cap in _both_reducers(stat):                        # « Cards » des deux côtés
                scenario = build(label("planchers", stat, f"cartes {both_text} contre cartes {other_text}"),
                                 ally_hand(both_cap), enemy_hand(ability=other_cap, power=8, damage=8), FLOORS_CONTEXT)
                yield scenario
                yield scenario.mirrored()


# --- Famille « persistants » : effets actifs, nouveaux effets, suspension, KO -------------------

def _effect(kind: str, value: int, borne: int) -> Tuple[int, int, int]:
    return (EFFECT_KINDS.index(kind), value, borne)


LOSS_KINDS, GAIN_KINDS = ("poison", "toxine", "consume", "combust"), ("heal", "regen", "dope", "repair")
TICK_SHAPES = {True: ((2, 0), (3, 2), (1, -1), (5, 3)), False: ((2, 14), (3, -1), (1, 13), (4, 12))}   # perte / gain
TICK_STOCKS = {True: ((12, 12), (3, 3), (2, 2), (1, 1)), False: ((12, 12), (13, 13), (14, 14), (11, 11))}


def _persistent_capacities() -> List[Tuple[str, Capacity]]:
    return [(text, cap) for text, cap in distinct_capacities() if any(kind in cap.types for kind in EFFECT_KINDS)]


def _all_kinds_but(kind: str) -> Tuple[Tuple[int, int, int], ...]:
    return tuple(_effect(other, 1, 0 if other in LOSS_KINDS else 15) for other in EFFECT_KINDS if other != kind)


def persistents_scenarios() -> Iterator[Scenario]:
    neutral = Context("r2", nb_turn=2, ally_won_last=False, ally_pillz=2, enemy_pillz=2)   # 14 contre 12 : l'allié gagne
    for kind in EFFECT_KINDS:                                   # 1. tics seuls, autour de la borne, sur chaque camp
        loss = kind in LOSS_KINDS
        for (value, borne), (life, pillz) in product(TICK_SHAPES[loss], TICK_STOCKS[loss]):
            ctx = replace(neutral, name=f"tic-{kind}-{value}-borne-{borne}-stock-{life}", ally_effects=(_effect(kind, value, borne),),
                          stocks=(life, pillz, 12, 12), ally_pillz=min(pillz + 1, 2))
            scenario = build("persistants/tic", ally_hand(), enemy_hand(), ctx)
            yield scenario
            yield scenario.mirrored()
    for text, cut in _persistent_capacities():                  # 2. chaque capacité persistante × effets déjà actifs × issue
        kind = next(type_ for type_ in cut.types if type_ in EFFECT_KINDS)
        target_is_enemy = cut.target == "enemy"
        for existing_name, ally_effects, enemy_effects in (
                ("aucun", (), ()),
                ("meme-sorte", () if target_is_enemy else (_effect(kind, 1, 0 if kind in LOSS_KINDS else 15),),
                 (_effect(kind, 1, 0 if kind in LOSS_KINDS else 15),) if target_is_enemy else ()),
                ("autres-sortes", _all_kinds_but(kind), _all_kinds_but(kind))):
            for ctx in (WIN_R1, LOSE_R1):
                stocks = (10, 9, 8, 10)
                scenario = build(label("persistants", text, existing_name), ally_hand(cut), enemy_hand(),
                                 replace(ctx, ally_effects=ally_effects, enemy_effects=enemy_effects, stocks=stocks))
                yield scenario
                yield scenario.mirrored()
        for probe_name in ("annule-vie", "annule-pillz"):       # 3. suspension par un Annul adverse
            probe = capacity(_PROBE_BY_NAME[probe_name])
            ctx = replace(WIN_R1, stocks=(10, 9, 8, 10), ally_effects=_all_kinds_but(""), enemy_effects=_all_kinds_but(""))
            scenario = build(label("persistants", text, probe_name), ally_hand(cut), enemy_hand(ability=probe), ctx)
            yield scenario
            yield scenario.mirrored()
    for case, stocks, ally_effects, enemy_effects in (   # 4. KO par un effet, sur un camp ou les deux
            ("ko-poison-allie", (2, 12, 12, 12), (_effect("poison", 2, 0),), ()),
            ("ko-poison-ennemi", (12, 12, 2, 12), (), (_effect("poison", 3, 0),)),
            ("ko-poison-les-deux", (1, 12, 2, 12), (_effect("poison", 1, 0),), (_effect("poison", 2, 0),)),
            ("ko-combust-allie", (2, 12, 12, 12), (_effect("combust", 2, 0),), ()),
            ("poison-borne-sauve", (2, 12, 12, 12), (_effect("poison", 2, 1),), ())):
        for ctx in (WIN_R1, LOSE_R1):
            scenario = build(label("persistants", case), ally_hand(), enemy_hand(),
                             replace(ctx, stocks=stocks, ally_effects=ally_effects, enemy_effects=enemy_effects))
            yield scenario
            yield scenario.mirrored()
    for text in ("Team: Cancel Players Life Mod.", "Team: Cancel Players Pillz Mod."):   # 5. Annul des deux côtés (Leader)
        leader = card("L", 5, 4, clan="Leader", ability=capacity(text))
        for probe_text, _ in _persistent_capacities()[:20]:
            ctx = replace(WIN_R1, stocks=(10, 9, 8, 10), ally_effects=_all_kinds_but(""), enemy_effects=_all_kinds_but(""))
            scenario = build(label("persistants", text, probe_text), ally_hand(capacity(probe_text))[:3] + (leader,), enemy_hand(), ctx)
            yield scenario
            yield scenario.mirrored()


# --- Famille « leaders » : Team, Leader unique, Counter-attack, Tie-break, Limitless -------------

def _leader(text: str, name: str = "L") -> CompiledCard:
    return card(name, 5, 4, clan="Leader", ability=capacity(text))


def leaders_scenarios() -> Iterator[Scenario]:
    team = [(text, cap) for text, cap in distinct_capacities() if "team" in cap.effect_conditions]
    for text, cut in team:
        leader = _leader(text)
        hands = (("leader-en-main", ally_hand()[:3] + (leader,), PLAYED_INDEX),
                 ("leader-joue", ally_hand()[:3] + (leader,), 3),
                 ("deux-exemplaires", ally_hand()[:2] + (_leader(text, "L2"), leader), PLAYED_INDEX),
                 ("deux-leaders", ally_hand()[:2] + (_leader("Team: +1 Damage", "L2"), leader), PLAYED_INDEX))
        contexts = base_contexts(rounds=ROUNDS[:2]) + [Context("r1-premier-gagne-sans-killshot", ally_pillz=3, enemy_pillz=2),
                                                        Context("r1-premier-gagne-perfect", ally_pillz=2, enemy_pillz=2)]
        for hand_name, ally, played in hands:
            for ctx in contexts:
                scenario = build(label("leaders", text, hand_name), ally, enemy_hand(), replace(ctx, ally_index=played))
                yield scenario
                yield scenario.mirrored()
    ashigaru = _leader("Counter-attack")                        # les deux camps avec, un seul, en premier / second
    for ctx in base_contexts(rounds=ROUNDS[:2]):
        scenario = build("leaders/Counter-attack/les-deux-camps", ally_hand()[:3] + (ashigaru,), enemy_hand()[:3] + (_leader("Counter-attack", "LE"),), ctx)
        yield scenario
        yield scenario.mirrored()
    solomon = _leader("Tie-break")                              # égalité d'attaque 42 = 42 : étoiles, premier joueur, Tie-break
    for ally_stars, enemy_stars, ally_first, holders in product((2, 3, 4), (3,), (True, False), ("allie", "ennemi", "les-deux", "aucun")):
        ally = ally_hand(stars=ally_stars)[:3] + ((solomon,) if holders in ("allie", "les-deux") else (card("A3", 7, 4, ally_stars),))
        enemy = enemy_hand(stars=enemy_stars)[:3] + ((_leader("Tie-break", "LE"),) if holders in ("ennemi", "les-deux") else (card("E3", 6, 5, enemy_stars),))
        ctx = Context(f"{ally_stars}-etoiles-contre-{enemy_stars}-{'premier' if ally_first else 'second'}", ally_first=ally_first, ally_pillz=6, enemy_pillz=7)
        yield build(label("leaders", "Tie-break", holders), ally, enemy, ctx)
    fractal = _leader("Limitless")                              # toutes les capacités bornées, en pouvoir (touchées) et en bonus (intactes)
    for text, cut in distinct_capacities():
        if cut.borne == -1:
            continue
        yield build(label("leaders", "Limitless", "pouvoir", text), ally_hand(cut)[:3] + (fractal,), enemy_hand(), WIN_R1)
        yield build(label("leaders", "Limitless", "pouvoir", text), ally_hand(cut)[:3] + (fractal,), enemy_hand(), LOSE_R1)
    for text, cut in distinct_capacities()[:40]:
        if cut.borne != -1:
            yield build(label("leaders", "Limitless", "bonus", text), ally_hand(None, cut)[:3] + (fractal,), enemy_hand(), WIN_R1)


# --- Famille « oculus » : Infiltrated et compositions de main -----------------------------------

def _clan_card(name: str, clan: str, ability: Optional[Capacity] = None) -> CompiledCard:
    """Carte d'un clan avec son vrai bonus (None pour un Leader : « Cancel Leader » n'a pas d'effet propre)."""
    return card(name, ALLY_POWER, ALLY_DAMAGE, clan=clan, ability=ability, bonus=parse_capacity(clan_bonus_texts()[clan]).capacity)


def oculus_scenarios() -> Iterator[Scenario]:
    infiltrated = capacity("Infiltrated")
    abilities = [(text, cap) for text, cap in distinct_capacities() if _clans_of(cap, "infiltrated")]
    for text, cut in abilities:
        listed = _clans_of(cut, "infiltrated")[0]
        unlisted = _clan_not_in(_clans_of(cut, "infiltrated"))
        third = _clan_not_in(_clans_of(cut, "infiltrated") + [unlisted])
        oculus = card("O", ALLY_POWER, ALLY_DAMAGE, clan="Oculus", ability=cut, bonus=infiltrated)
        second_oculus = card("O2", ALLY_POWER, ALLY_DAMAGE, clan="Oculus", ability=cut, bonus=infiltrated)
        hands = (("un-clan-liste", (_clan_card("A0", listed), oculus, _clan_card("A2", listed), _clan_card("A3", listed))),
                 ("un-clan-non-liste", (_clan_card("A0", unlisted), oculus, _clan_card("A2", unlisted), _clan_card("A3", unlisted))),
                 ("carte-seule-listee", (_clan_card("A0", unlisted), oculus, _clan_card("A2", unlisted), _clan_card("A3", listed))),
                 ("carte-seule-non-listee", (_clan_card("A0", listed), oculus, _clan_card("A2", listed), _clan_card("A3", unlisted))),
                 ("trois-clans", (_clan_card("A0", listed), oculus, _clan_card("A2", unlisted), _clan_card("A3", third))),
                 ("deux-oculus", (_clan_card("A0", listed), oculus, second_oculus, _clan_card("A3", listed))),
                 ("leader-seul", (_clan_card("A0", listed), oculus, _clan_card("A2", listed), _leader("Team: +1 Damage"))))
        for hand_name, ally in hands:
            for ctx in (WIN_R1, LOSE_R1):
                scenario = build(label("oculus", text, hand_name), ally, enemy_hand(), ctx)
                yield scenario
                yield scenario.mirrored()
        support = _clan_card("A0", listed, ability=capacity("Support: Power +1"))   # l'Oculus en main compte pour Support
        yield build(label("oculus", text, "oculus-en-main-support"), (support, oculus, _clan_card("A2", listed), _clan_card("A3", listed)),
                    enemy_hand(), replace(WIN_R1, ally_index=0))


# --- Famille « combat » : égalités, KO, Reanimate, fin de partie, bords des mises ----------------

def combat_scenarios() -> Iterator[Scenario]:
    for ally_stars, enemy_stars, ally_first in product((2, 3, 4), (2, 3, 4), (True, False)):     # égalité 42 = 42
        ctx = Context(f"{ally_stars}-contre-{enemy_stars}-{'premier' if ally_first else 'second'}", ally_first=ally_first, ally_pillz=6, enemy_pillz=7)
        yield build("combat/egalite", ally_hand(stars=ally_stars), enemy_hand(stars=enemy_stars), ctx)
    for life, enemy_bet in product((1, 3, 5, 6, 7), (6,)):                                          # KO : dégâts 5 (+2 fury)
        for fury in (False, True):
            ctx = Context(f"vie-{life}-{'fury' if fury else 'sans-fury'}", ally_pillz=1, enemy_pillz=enemy_bet, enemy_fury=fury, stocks=(life, 12, 12, 12))
            scenario = build("combat/ko", ally_hand(), enemy_hand(), ctx)
            yield scenario
            yield scenario.mirrored()
    for text in ("Reanimate: +1 Life", "Reanimate: +2 Life", "Reanimate: +3 Life", "Support: Reanimate: +1 Life", "Degrowth: Reanimate: +1 Life", "Brawl: Reanimate: +1 Life"):
        for life in (1, 5, 6):
            for placement in ("pouvoir", "bonus"):
                ally = ally_hand(capacity(text)) if placement == "pouvoir" else ally_hand(None, capacity(text))
                ctx = Context(f"vie-{life}", ally_pillz=1, enemy_pillz=6, stocks=(life, 12, 12, 12))
                scenario = build(label("combat", "reanimate", placement, text), ally, enemy_hand(), ctx)
                yield scenario
                yield scenario.mirrored()
        scenario = build(label("combat", "reanimate", text, "ko-par-poison"), ally_hand(capacity(text)), enemy_hand(),
                         replace(WIN_R1, stocks=(2, 12, 12, 12), ally_effects=(_effect("poison", 2, 0),)))
        yield scenario
        yield scenario.mirrored()
    for ally_life, enemy_life in ((12, 12), (8, 5), (5, 8), (4, 4)):                                # dernier round : fin de partie
        for wins in (True, False):
            ctx = _outcome_context(f"vies-{ally_life}-{enemy_life}-{'gagne' if wins else 'perd'}", 4, True, False, wins, stocks=(ally_life, 4, enemy_life, 3))
            yield build("combat/fin-de-partie", ally_hand(), enemy_hand(), ctx)
    for stocks, ally_bet, ally_fury, enemy_bet, enemy_fury in (                                     # bords des mises
            ((12, 0, 12, 0), 1, False, 1, False), ((12, 3, 12, 3), 1, True, 1, True), ((12, 12, 12, 12), 13, False, 13, False),
            ((12, 12, 12, 12), 10, True, 10, True), ((12, 5, 12, 2), 3, True, 3, False), ((12, 1, 12, 1), 2, False, 2, False)):
        ctx = Context(f"stock-{stocks[1]}-{stocks[3]}-mises-{ally_bet}{'f' if ally_fury else ''}-{enemy_bet}{'f' if enemy_fury else ''}",
                      ally_pillz=ally_bet, ally_fury=ally_fury, enemy_pillz=enemy_bet, enemy_fury=enemy_fury, stocks=stocks)
        scenario = build("combat/mises", ally_hand(), enemy_hand(), ctx)
        yield scenario
        yield scenario.mirrored()
    for text in ("-7 Cards Attack, Min 0", "-4 Opp Power, Min 0", "-4 Cards Damage, Min 0", "Tune Out"):   # attaques et dégâts nuls
        for ctx in (Context("mises-1-1"), Context("mises-2-2", ally_pillz=2, enemy_pillz=2), Context("second-mises-1-1", ally_first=False)):
            scenario = build(label("combat", "zero", text), ally_hand(capacity(text)), enemy_hand(), ctx)
            yield scenario
            yield scenario.mirrored()


# --- Famille « aleatoire » : parties complètes jouées au hasard --------------------------------

def random_scenarios(games: int = 300, extra_pairs: int = 4, seed: int = 0) -> Iterator[Scenario]:
    """Chaque état d'une partie aléatoire, avec le coup joué et quelques paires d'actions non jouées."""
    rng = random.Random(seed)
    for number in range(games):
        game = Game(1, rng.random() < 0.5, Player("ally", 12, 12), Player("enemy", 12, 12), [])
        game.ally.cards, game.enemy.cards = random_hand(rng), random_hand(rng)
        deck, state = deck_from_game(game), state_from_game(game)
        while terminal(state) is None:
            pairs = [(rng.choice(legal_actions(state, "ally")), rng.choice(legal_actions(state, "enemy"))) for _ in range(1 + extra_pairs)]
            for index, (ally_action, enemy_action) in enumerate(pairs):
                yield Scenario(f"aleatoire/partie-{number}/round-{state.nb_turn}/coup-{index}", deck, state, ally_action, enemy_action)
            state = step(deck, state, *pairs[0])


FAMILIES = {
    "solo": solo_scenarios,
    "interactions": interactions_scenarios,
    "planchers": floors_scenarios,
    "persistants": persistents_scenarios,
    "leaders": leaders_scenarios,
    "oculus": oculus_scenarios,
    "combat": combat_scenarios,
    "aleatoire": random_scenarios,
}
