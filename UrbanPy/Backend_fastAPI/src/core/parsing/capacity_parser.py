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
# Bonus des Leaders : deux Leaders en main s'annulent ; le moteur l'applique via la règle « Leader unique »
# (process_round.leader_team_capacity), le bonus lui-même n'a pas d'effet propre.
CANCEL_LEADER = ParsedCapacity(capacity=None, supported=True, reason="cancel leader: géré par la règle du Leader unique")

# Synonymes mot à mot (le point final est retiré avant la recherche)
_WORD_SYNONYMS = {
    "pow": "power", "dam": "damage", "dmg": "damage",
    "atk": "attack", "att": "attack",
    "mod": "modif",
    "prot": "protection", "protec": "protection", "protect": "protection",
    "canc": "cancel", "rec": "recover", "recov": "recover",
    "conf": "confidence", "vict": "victory", "def": "defeat",
    "rev": "revenge", "repris": "reprisal", "asy": "asymmetry", "asym": "asymmetry", "asymm": "asymmetry",
    "brwl": "brawl",
}


def normalize(text: str) -> str:
    """Texte en minuscules, synonymes unifiés, ':' isolé par des espaces, virgules retirées."""
    t = text.lower().strip()
    t = t.replace("&", " and ").replace(";", ":")
    t = t.replace("pow/dam", "power and damage")
    t = t.replace("/", " per ")                          # "+1 Dam./ Life Lost" = par vie perdue
    t = re.sub(r"([+-])\s+(\d)", r"\1\2", t)          # "- 2" -> "-2"
    t = t.replace(",", " ")
    t = re.sub(r"\s*:\s*", " : ", t)                   # ':' devient un mot à part entière
    words = []
    for word in t.split():
        bare = word.rstrip(".")
        words.append(_WORD_SYNONYMS.get(bare, bare))
    t = " ".join(words)
    t = re.sub(r"(^|: )(-\d+) pillz opp\b", r"\1\2 opp pillz", t)   # "-2 pillz opp" -> "-2 opp pillz"
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
    "stop": "stop",           # l'ability n'agit que si elle a été stoppée (évalué au niveau 1)
    "killshot": "killshot",   # attaque >= 2 x attaque adverse (évalué après le calcul des attaques)
    "perfect": "perfect",     # écart d'attaque < puissance : une pillz de moins n'aurait pas gagné (idem)
    "team": "team",           # ability de Leader : s'applique à chaque carte jouée de l'équipe (voir process_round)
    "unison": "unison",       # la main est exclusivement du clan de la carte
    "disunion": "disunion",   # au moins une carte d'un autre clan dans la main
}
_MULTIPLIER_PREFIXES = ("support", "growth", "degrowth", "equalizer", "brawl")
_IGNORED_PREFIXES = ("day",)   # cycle jour/nuit non modélisé : Day toujours valide, donc Night jamais
_UNSUPPORTED_PREFIXES = ("versus", "after", "infiltrated", "night")   # sans clan : données anciennes
_R_BET = re.compile(r"^bet ([<>]) (\d+) pillz$")   # « Bet > 4 pillz » : pillz misées ce round
_CORE_STARTERS = ("copy", "protection", "reanimate")   # mots qui ouvrent un cœur contenant ':'

# Cœurs connus mais hors moteur : testés avant les regex, raison groupable dans le rapport
_UNSUPPORTED_CORE_KEYWORDS = (
    "remove ability conditions", "counter-attack", "tie-break",
    "fatal killshot", "sinister symmetry", "tune out", "overdose", "perfection",
    "rebirth",
    "beyond", "bypass", "hazard", "illusion", "limitless",
)

# --- Cœurs ------------------------------------------------------------------------------------

_STAT = r"power and damage|pillz and life|life and pillz|power|damage|attack|life|pillz"
_COMPOSITE_TYPES = {"power and damage": ["power", "damage"], "pillz and life": ["pillz", "life"], "life and pillz": ["pillz", "life"]}
_PER_MULTIPLIERS = {
    "pillz left": "nb_pillz_left", "life left": "nb_life_left",
    "life lost": "nb_life_lost", "pillz lost": "nb_pillz_lost", "opp damage": "nb_dam_opp",
    "damage": "nb_damage",   # dégâts réellement infligés par la carte ce round
    "opp power": "nb_pow_opp",
}

_R_STAT_PLUS = re.compile(r"^(?:(opp) )?(power and damage|power|damage|attack) \+(\d+)(?: max (\d+))?$")
_R_PLUS = re.compile(rf"^\+(\d+) (?:(opp|players) )?({_STAT})(?: per (.+?))?(?: max (\d+))?$")
_R_MINUS_OPP = re.compile(rf"^-(\d+) opp ({_STAT})(?: per (.+?))? min (\d+)$")
_R_MINUS_SELF = re.compile(r"^-(\d+) (?:(players) )?(life|pillz) min (\d+)$")

_R_STOP = re.compile(r"^stop (?:opp )?(ability|bonus)$")
_R_COPY = re.compile(r"^copy (?:opp )?(ability|bonus|power and damage|power|damage)(?: opp)?$")
_R_PROTECTION = re.compile(r"^protection (ability|bonus|power and damage|power|damage|attack)$")
_R_PROTECTION_SUFFIX = re.compile(r"^(ability|bonus) protection$")
_R_CANCEL = re.compile(r"^cancel (?:opp )?(power and damage|pillz and life|power|damage|attack|life|pillz) modif$")
_R_EXCHANGE = re.compile(r"^(power and damage|power|damage) exchange$")
_R_IMPOSE = re.compile(r"^(power|damage) impose$")   # la stat adverse prend la valeur imprimée de ma carte
_R_PERSISTENT = re.compile(r"^(?:(players) )?(poison|toxin|heal|regen|dope|repair|consume|combust|mindwipe) (\d+) (?:min|max) (\d+)$")
_R_CORRUPT = re.compile(r"^corrupt (\d+) min (\d+)$")           # le propriétaire perd X vies, victoire ou défaite
_R_CORROSION = re.compile(r"^corrosion (\d+) min (\d+)$")   # poison dont la valeur est multipliée par le numéro du round
_R_REANIMATE = re.compile(r"^reanimate \+(\d+) life$")
_R_RECOVER = re.compile(r"^recover (\d+) pillz out of (\d+)$")   # X pillz récupérées sur Y misées (fin de round)
_R_INFILTRATED = re.compile(r"^infiltrated$")                        # bonus Oculus : adopte le bonus du clan majoritaire de la main

# Mindwipe : « lose X Life Points and Pillz, minimum Y, at the end of each of the following rounds » = Combust (textes officiels)
_PERSISTENT_TYPES = {"poison": "poison", "toxin": "toxine", "heal": "heal", "regen": "regen", "dope": "dope", "repair": "repair",
                     "consume": "consume", "combust": "combust", "mindwipe": "combust"}
_PERSISTENT_TARGETS = {"poison": "enemy", "toxin": "enemy", "heal": "ally", "regen": "ally", "dope": "ally", "repair": "ally",
                       "consume": "enemy", "combust": "enemy", "mindwipe": "enemy"}


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


_R_CARDS = re.compile(r"\bcards\b")


def _parse_core(core: str, conditions: list, prefix_hows: list) -> ParsedCapacity:
    """« Cards » (ex. « -2 Cards Damage, Min 1 », « Protection: Cards Power ») : l'effet porte sur les deux cartes du round."""
    if _R_CARDS.search(core):
        stripped = _R_CARDS.sub("opp" if core.startswith("-") else "", core)
        parsed = _parse_core(re.sub(r"\s+", " ", stripped).strip(), conditions, prefix_hows)
        if parsed.supported and parsed.capacity is not None:
            parsed.capacity.target = "both"
        return parsed
    for keyword in _UNSUPPORTED_CORE_KEYWORDS:
        if re.search(rf"(?<![\w-]){re.escape(keyword)}(?![\w-])", core):
            return _unsupported(f"unsupported core: {keyword}")

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

    match = _R_IMPOSE.match(core)
    if match:
        return error or _capacity("enemy", [match.group(1)], 0, "impose", -1, conditions)

    match = _R_PERSISTENT.match(core)
    if match:
        players, effect, value, borne = match.groups()
        target = "both" if players else _PERSISTENT_TARGETS[effect]
        return error or _capacity(target, [_PERSISTENT_TYPES[effect]], int(value), how, int(borne), conditions)

    match = _R_CORRUPT.match(core)
    if match:
        return error or _capacity("ally", ["life"], -int(match.group(1)), how, int(match.group(2)), conditions + ["victory_defeat"])

    match = _R_CORROSION.match(core)
    if match:
        how, error = _resolve_how(prefix_hows + ["growth"], None)
        return error or _capacity("enemy", ["poison"], int(match.group(1)), how, int(match.group(2)), conditions)

    match = _R_REANIMATE.match(core)
    if match:
        return error or _capacity("ally", ["reanimate"], int(match.group(1)), how, -1, conditions)

    match = _R_RECOVER.match(core)
    if match:
        return error or _capacity("ally", ["recover"], int(match.group(1)), how, int(match.group(2)), conditions)

    if _R_INFILTRATED.match(core):
        return error or _capacity("ally", ["infiltrated"], 0, how, -1, conditions)

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


# Préfixes à clans (rendus en texte par le scraper depuis les icônes) : « Versus Freaks, Oculus: … », « After Tolvack: … »,
# « Infiltrated La Junta, Piranas: … » (Oculus : l'ability n'agit que si l'Oculus a infiltré l'un de ces clans).
_R_CLAN_PREFIX = re.compile(r"(^|:)\s*(versus|after|infiltrated)\s+([^:]+?)\s*:", re.IGNORECASE)


def _extract_clan_conditions(text: str):
    """
    Retire les préfixes à clans (en tête ou après un autre préfixe) et renvoie (texte restant, conditions
    « versus:Clan|Clan » / « after:… » / « infiltrated:… »). Les clans gardent leur casse (comparés à card.faction).
    Sans clan (ancien scraping où le clan était une image) le texte est laissé tel quel.
    """
    conditions = []
    while True:
        match = _R_CLAN_PREFIX.search(text)
        if not match:
            return text, conditions
        clans = [clan.strip() for clan in match.group(3).split(",") if clan.strip()]
        if not clans:
            return text, conditions
        conditions.append(f"{match.group(2).lower()}:" + "|".join(clans))
        text = text[:match.start()] + match.group(1) + text[match.end():]


def parse_capacity(text: str) -> ParsedCapacity:
    text, clan_conditions = _extract_clan_conditions(text or "")
    normalized = normalize(text)
    if normalized in ("", "no ability") or re.fullmatch(r"ability at level \d+", normalized):
        return NO_ABILITY
    if normalized == "cancel leader":
        return CANCEL_LEADER

    segments = [segment.strip() for segment in normalized.split(" : ")]
    conditions, prefix_hows = [], []
    index = 0
    while index < len(segments) - 1:          # le dernier segment est toujours (la fin du) cœur
        segment = segments[index]
        bet = _R_BET.match(segment)
        if segment in _CONDITION_PREFIXES:
            conditions.append(_CONDITION_PREFIXES[segment])
        elif bet:
            conditions.append(f"bet{bet.group(1)}{bet.group(2)}")
        elif segment in _MULTIPLIER_PREFIXES:
            prefix_hows.append(segment)
        elif segment == "xantiax":            # « Xantiax: -X Life, Min Y » : les deux joueurs, victoire ou défaite
            conditions.append("victory_defeat")
            segments[-1] = re.sub(r"^(-\d+) life", r"\1 players life", segments[-1])
        elif segment in _IGNORED_PREFIXES:
            pass
        elif segment in _UNSUPPORTED_PREFIXES:
            return _unsupported(f"unsupported prefix: {segment}")
        elif segment in _CORE_STARTERS:
            break
        else:
            return _unsupported(f"unknown prefix: {segment}")
        index += 1
    conditions.extend(clan_conditions)
    core = " ".join(segments[index:])
    return _parse_core(core, conditions, prefix_hows)
