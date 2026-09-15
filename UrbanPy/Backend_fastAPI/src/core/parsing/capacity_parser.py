"""
Parseur des descriptions textuelles d'abilities / bonus (ex. "Growth: -1 Opp Power, Min 4")
vers des objets Capacity au vocabulaire exact du moteur. Fonction pure, ne lève jamais.
Voir docs/superpowers/specs/2026-09-15-capacity-parser-design.md.
"""
import re
from dataclasses import dataclass
from typing import Optional

from src.core.domain.capacity import Capacity


@dataclass(frozen=True)
class ParsedCapacity:
    capacity: Optional[Capacity]
    supported: bool
    reason: str = ""


NO_ABILITY = ParsedCapacity(capacity=None, supported=True, reason="no ability")

# Synonymes mot à mot (le point final est retiré avant la recherche)
_WORD_SYNONYMS = {
    "pow": "power", "dam": "damage", "dmg": "damage",
    "atk": "attack", "att": "attack",
    "mod": "modif",
    "prot": "protection", "protec": "protection", "protect": "protection",
    "canc": "cancel", "rec": "recover",
    "conf": "confidence", "vict": "victory", "def": "defeat",
}


def normalize(text: str) -> str:
    """Texte en minuscules, synonymes unifiés, ':' isolé par des espaces, virgules retirées."""
    t = text.lower().strip()
    t = t.replace("&", " and ").replace(";", ":")
    t = t.replace("pow/dam", "power and damage")
    t = re.sub(r"([+-])\s+(\d)", r"\1\2", t)          # "- 2" -> "-2"
    t = t.replace(",", " ")
    t = re.sub(r"\s*:\s*", " : ", t)                   # ':' devient un mot à part entière
    words = []
    for word in t.split():
        bare = word.rstrip(".")
        words.append(_WORD_SYNONYMS.get(bare, bare))
    t = " ".join(words)
    t = re.sub(r"^(-\d+) pillz opp\b", r"\1 opp pillz", t)
    return t


def _unsupported(reason: str) -> ParsedCapacity:
    return ParsedCapacity(capacity=None, supported=False, reason=reason)


def _capacity(target, types, value, how="", borne=-1, conditions=()) -> ParsedCapacity:
    capacity = Capacity(target=target, types=list(types), value=value, borne=borne, how=how,
                        effect_conditions=list(conditions), lvl_priority=0)
    return ParsedCapacity(capacity=capacity, supported=True, reason="")


# --- Préfixes ---------------------------------------------------------------------------------

_CONDITION_PREFIXES = {
    "courage": "courage", "revenge": "revenge", "confidence": "confidence", "reprisal": "reprisal",
    "symmetry": "symmetry", "asymmetry": "asymmetry", "defeat": "defeat", "backlash": "backlash",
    "victory or defeat": "victory_defeat",
}
_MULTIPLIER_PREFIXES = ("support", "growth", "degrowth", "equalizer", "brawl")
_UNSUPPORTED_PREFIXES = ("stop", "killshot", "day", "team", "versus", "xantiax")
_CORE_STARTERS = ("copy", "protection", "reanimate")   # mots qui ouvrent un cœur contenant ':'

# --- Cœurs ------------------------------------------------------------------------------------

_STAT = r"power and damage|pillz and life|life and pillz|power|damage|attack|life|pillz"
_COMPOSITE_TYPES = {"power and damage": ["power", "damage"], "pillz and life": ["pillz", "life"], "life and pillz": ["pillz", "life"]}
_PER_MULTIPLIERS = {
    "pillz left": "nb_pillz_left", "life left": "nb_life_left",
    "life lost": "nb_life_lost", "pillz lost": "nb_pillz_lost", "opp damage": "nb_dam_opp",
}

_R_STAT_PLUS = re.compile(r"^(?:(opp) )?(power and damage|power|damage|attack) \+(\d+)(?: max (\d+))?$")
_R_PLUS = re.compile(rf"^\+(\d+) (?:(opp|players) )?({_STAT})(?: per (.+?))?(?: max (\d+))?$")
_R_MINUS_OPP = re.compile(rf"^-(\d+) opp ({_STAT})(?: per (.+?))? min (\d+)$")
_R_MINUS_SELF = re.compile(r"^-(\d+) (?:(players) )?(life|pillz) min (\d+)$")

_R_STOP = re.compile(r"^stop (?:opp )?(ability|bonus)$")
_R_COPY = re.compile(r"^copy (?:opp )?(ability|bonus|power and damage|power|damage)(?: opp)?$")
_R_PROTECTION = re.compile(r"^protection (ability|bonus|power and damage|power|damage|attack)$")
_R_PROTECTION_SUFFIX = re.compile(r"^(ability|bonus) protection$")
_R_CANCEL = re.compile(r"^cancel opp (power and damage|pillz and life|power|damage|attack|life|pillz) modif$")
_R_EXCHANGE = re.compile(r"^(power and damage|power|damage) exchange$")
_R_PERSISTENT = re.compile(r"^(poison|toxin|heal|regen|dope) (\d+) (?:min|max) (\d+)$")
_R_REANIMATE = re.compile(r"^reanimate \+(\d+) life$")

_PERSISTENT_TYPES = {"poison": "poison", "toxin": "toxine", "heal": "heal", "regen": "regen", "dope": "dope"}
_PERSISTENT_TARGETS = {"poison": "enemy", "toxin": "enemy", "heal": "ally", "regen": "ally", "dope": "ally"}


def _types(stat: str) -> list:
    return list(_COMPOSITE_TYPES.get(stat, [stat]))


def _borne(group) -> int:
    return int(group) if group is not None else -1


def _resolve_how(prefix_hows: list, per: Optional[str]):
    """Retourne (how, erreur) : un seul multiplicateur autorisé."""
    hows = list(prefix_hows)
    if per is not None:
        if per not in _PER_MULTIPLIERS:
            return None, _unsupported(f"unsupported multiplier: per {per}")
        hows.append(_PER_MULTIPLIERS[per])
    if len(hows) > 1:
        return None, _unsupported("unsupported: two multipliers")
    return (hows[0] if hows else ""), None


def _parse_core(core: str, conditions: list, prefix_hows: list) -> ParsedCapacity:
    how, error = _resolve_how(prefix_hows, None)   # les cœurs ci-dessous n'ont pas de suffixe "per"

    match = _R_STOP.match(core)
    if match:
        return error or _capacity("enemy", [match.group(1)], 0, "stop", -1, conditions)

    match = _R_COPY.match(core)
    if match:
        return error or _capacity("enemy", _types(match.group(1)), 0, "copy", -1, conditions)

    match = _R_PROTECTION.match(core) or _R_PROTECTION_SUFFIX.match(core)
    if match:
        return error or _capacity("ally", _types(match.group(1)), 0, "Protection", -1, conditions)

    match = _R_CANCEL.match(core)
    if match:
        return error or _capacity("enemy", _types(match.group(1)), 0, "cancel", -1, conditions)

    match = _R_EXCHANGE.match(core)
    if match:
        return error or _capacity("both", _types(match.group(1)), 0, "exchange", -1, conditions)

    match = _R_PERSISTENT.match(core)
    if match:
        effect, value, borne = match.groups()
        return error or _capacity(_PERSISTENT_TARGETS[effect], [_PERSISTENT_TYPES[effect]], int(value), how, int(borne), conditions)

    match = _R_REANIMATE.match(core)
    if match:
        return error or _capacity("ally", ["reanimate"], int(match.group(1)), how, -1, conditions)

    match = _R_STAT_PLUS.match(core)
    if match:
        opp, stat, value, borne = match.groups()
        how, error = _resolve_how(prefix_hows, None)
        return error or _capacity("enemy" if opp else "ally", _types(stat), int(value), how, _borne(borne), conditions)

    match = _R_PLUS.match(core)
    if match:
        value, who, stat, per, borne = match.groups()
        how, error = _resolve_how(prefix_hows, per)
        target = {"opp": "enemy", "players": "both"}.get(who, "ally")
        return error or _capacity(target, _types(stat), int(value), how, _borne(borne), conditions)

    match = _R_MINUS_OPP.match(core)
    if match:
        value, stat, per, borne = match.groups()
        how, error = _resolve_how(prefix_hows, per)
        return error or _capacity("enemy", _types(stat), -int(value), how, int(borne), conditions)

    match = _R_MINUS_SELF.match(core)
    if match:
        value, players, stat, borne = match.groups()
        how, error = _resolve_how(prefix_hows, None)
        return error or _capacity("both" if players else "ally", [stat], -int(value), how, int(borne), conditions)

    return _unsupported("unknown core")


def parse_capacity(text: str) -> ParsedCapacity:
    normalized = normalize(text or "")
    if normalized in ("", "no ability") or re.fullmatch(r"ability at level \d+", normalized):
        return NO_ABILITY

    segments = [segment.strip() for segment in normalized.split(" : ")]
    conditions, prefix_hows = [], []
    index = 0
    while index < len(segments) - 1:          # le dernier segment est toujours (la fin du) cœur
        segment = segments[index]
        if segment in _CONDITION_PREFIXES:
            conditions.append(_CONDITION_PREFIXES[segment])
        elif segment in _MULTIPLIER_PREFIXES:
            prefix_hows.append(segment)
        elif segment in _UNSUPPORTED_PREFIXES:
            return _unsupported(f"unsupported prefix: {segment}")
        elif segment in _CORE_STARTERS:
            break
        else:
            return _unsupported(f"unknown prefix: {segment}")
        index += 1
    core = " ".join(segments[index:])
    return _parse_core(core, conditions, prefix_hows)
