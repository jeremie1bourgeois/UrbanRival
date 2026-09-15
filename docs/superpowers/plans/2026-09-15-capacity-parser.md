# Parseur de capacités — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer le texte des abilities/bonus de `jsonData_officiel.json` en objets `Capacity`, l'intégrer au chargement des cartes, et rendre `POST /init_game/` jouable avec n'importe quelle carte.

**Architecture:** Un module pur `src/core/parsing/capacity_parser.py` (normalisation → préfixes → cœur par regex) produit `ParsedCapacity(capacity | None, supported, reason)` sans jamais lever. Un repository `card_repository.py` charge le JSON officiel une fois via `BASE_DIR` ; `Card.__init__` l'utilise et appelle le parseur. Deux garde-fous dans `process_round.check_capacity_condition` (capacité `None`, conditions différées) et la vérification des conditions sur la copie de combat. Un script `scripts/capacity_coverage.py` liste ce que le moteur ne gère pas encore.

**Tech Stack:** Python 3.12, `re`, `dataclasses`, pytest (venv : `pip install -r requirements-dev.txt`). Aucune dépendance nouvelle.

**Spec:** `docs/superpowers/specs/2026-09-15-capacity-parser-design.md`

## Global Constraints

- Tout se passe dans `UrbanPy/Backend_fastAPI/` ; les commandes ci-dessous supposent ce dossier courant.
- Tests : `python -m pytest -q -p no:warnings` (le venv du projet doit contenir `fastapi==0.100.0`, `pytest`, `httpx<0.28`).
- Fichiers existants en **CRLF** : les modifier sans changer les fins de ligne (Python : lire/écrire en mode binaire avec `\r\n`, ou `unix2dos` après édition). Nouveaux fichiers en LF.
- Le vocabulaire produit doit être **exactement** celui du moteur (spec §2) : `how` ∈ `"" support growth degrowth equalizer brawl nb_pillz_left nb_life_left nb_life_lost nb_pillz_lost nb_dam_opp stop copy Protection cancel exchange` ; `types` ∈ `power damage attack ability bonus life pillz reanimate poison toxine heal regen dope` ; `target` ∈ `ally enemy both` ; `lvl_priority` = 0.
- `parse_capacity` ne lève jamais d'exception.
- Une capacité non supportée → `capacity is None`, `supported=False`, `reason` non vide ; la carte reste jouable.
- Un commit par tâche, message en français, suffixe `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `src/core/parsing/__init__.py` | package (vide) |
| `src/core/parsing/capacity_parser.py` | `ParsedCapacity`, `normalize`, `parse_capacity` — pur, sans I/O |
| `src/adapters/repositories/card_repository.py` | lecture cachée de `data/jsonData_officiel.json`, `get_official_card`, `all_capacity_descriptions` |
| `src/core/domain/card.py` | `Card.__init__` via repository + parseur ; `from_dict_template` tolère `null` ; suppression de `from_dict` |
| `src/core/domain/player.py`, `game.py` | suppression de `from_dict` (chaîne morte) |
| `src/core/use_cases/process_round.py` | `check_capacity_condition` réécrite (None, conditions différées), appel sur `*_fight` |
| `src/core/services/game_service.py` | `create_game` : `nb_turn=1`, renvoie `(game, new_id)` |
| `main.py` | `POST /init_game/` renvoie `game_id` |
| `scripts/capacity_coverage.py` | rapport de couverture |
| `data/template_game_v1.json` | `Stop Opp. Bonus` : `value` 5 → 0 |
| `tests/test_capacity_parser.py`, `tests/test_card_loading.py` | nouveaux |
| `tests/test_process_round.py`, `tests/test_api.py` | complétés |

---

### Task 1 : Squelette du parseur, normalisation, « pas d'ability »

**Files:**
- Create: `src/core/parsing/__init__.py`, `src/core/parsing/capacity_parser.py`
- Test: `tests/test_capacity_parser.py`

**Interfaces:**
- Produces: `ParsedCapacity(capacity: Capacity | None, supported: bool, reason: str = "")` (dataclass gelée) ; `normalize(text: str) -> str` ; `parse_capacity(text: str) -> ParsedCapacity` ; constante `NO_ABILITY`.

- [ ] **Step 1 : Écrire les tests rouges**

```python
# tests/test_capacity_parser.py
import pytest

from src.core.parsing.capacity_parser import ParsedCapacity, normalize, parse_capacity


# --- Normalisation ----------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Equalizer: -1 Opp Pow. & Dam., Min 1", "equalizer : -1 opp power and damage min 1"),
    ("Reprisal: -X Opp Pow. & Dmg,min Y", "reprisal : -x opp power and damage min y"),
    ("Stop: Atk. +3", "stop : attack +3"),
    ("-4 Opp Att. Per Life Left, Min 2", "-4 opp attack per life left min 2"),
    ("Courage; -2 Opp Pillz. Min 1", "courage : -2 opp pillz min 1"),
    ("-2 Pillz Opp. Min 1", "-2 opp pillz min 1"),
    ("Conf.: Vict. Or Def.: -2 Opp. Life, Min 1", "confidence : victory or defeat : -2 opp life min 1"),
    ("Backlash: - 2 Life Min 0", "backlash : -2 life min 0"),
    ("Power And Damage + 2", "power and damage +2"),
    ("Cancel Opp. Pow/dam Mod.", "cancel opp power and damage modif"),
    ("Reprisal: Cancel Opp Pow & Dam Mod", "reprisal : cancel opp power and damage modif"),
    ("Courage: Prot.: Power & Damage", "courage : protection : power and damage"),
    ("Revenge: Protec. Power And Dmg", "revenge : protection power and damage"),
    ("Versus  : Power +2", "versus : power +2"),
    ("Growth : Power & Damage +1", "growth : power and damage +1"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


# --- Pas d'ability ----------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["", "   ", "No Ability", "Ability at Level 3", "Ability at Level 5"])
def test_no_ability_is_supported_and_empty(text):
    parsed = parse_capacity(text)

    assert parsed == ParsedCapacity(capacity=None, supported=True, reason="no ability")
```

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: erreur d'import `ModuleNotFoundError: No module named 'src.core.parsing'`.

- [ ] **Step 3 : Implémenter**

```python
# src/core/parsing/__init__.py
```
(fichier vide)

```python
# src/core/parsing/capacity_parser.py
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


def parse_capacity(text: str) -> ParsedCapacity:
    normalized = normalize(text or "")
    if normalized in ("", "no ability") or re.fullmatch(r"ability at level \d+", normalized):
        return NO_ABILITY
    return _unsupported("unknown core")
```

- [ ] **Step 4 : Vérifier que les tests passent**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: `20 passed`.

- [ ] **Step 5 : Commit**

```bash
git add src/core/parsing tests/test_capacity_parser.py
git commit -m "feat(parseur): squelette, normalisation du texte et cas « pas d'ability »

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2 : Modificateurs de stats, préfixes conditions/multiplicateurs, suffixe « per »

**Files:**
- Modify: `src/core/parsing/capacity_parser.py`
- Test: `tests/test_capacity_parser.py`

**Interfaces:**
- Consumes: `normalize`, `ParsedCapacity`, `_unsupported` (Task 1).
- Produces: `parse_capacity` gère les formes #9 à #12 de la spec et les préfixes ; helper interne `_capacity(target, types, value, how, borne, conditions) -> ParsedCapacity`.

- [ ] **Step 1 : Écrire les tests rouges** (ajouter à `tests/test_capacity_parser.py`)

```python
from src.core.domain.capacity import Capacity


def cap(target, types, value, how="", borne=-1, conditions=()):
    return Capacity(target=target, types=list(types), value=value, borne=borne, how=how,
                    effect_conditions=list(conditions)).to_dict()


def parsed(text):
    result = parse_capacity(text)
    assert result.supported is True, result.reason
    return result.capacity.to_dict()


# --- Golden : encodage manuel du template (spec §3) -------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("-2 Opp Power, Min 1", cap("enemy", ["power"], -2, borne=1)),
    ("Growth: -1 Opp Power, Min 4", cap("enemy", ["power"], -1, how="growth", borne=4)),
    ("Courage: Damage +3", cap("ally", ["damage"], 3, conditions=["courage"])),
    ("Power +4", cap("ally", ["power"], 4)),
    ("-3 Opp Damage, Min 2", cap("enemy", ["damage"], -3, borne=2)),
    ("Support: Damage +1", cap("ally", ["damage"], 1, how="support")),
    ("Equalizer: -1 Opp Pow. & Dam., Min 1", cap("enemy", ["power", "damage"], -1, how="equalizer", borne=1)),
    ("Support: Attack +3", cap("ally", ["attack"], 3, how="support")),
])
def test_golden_template_encodings(text, expected):
    assert parsed(text) == expected


# --- Formes de cœur : modificateurs -----------------------------------------------------------

def test_stat_plus_with_max():
    assert parsed("Power +2, Max. 8") == cap("ally", ["power"], 2, borne=8)


def test_plus_life_targets_ally():
    assert parsed("+3 Life") == cap("ally", ["life"], 3)


def test_plus_pillz_and_life():
    assert parsed("+2 Pillz And Life") == cap("ally", ["pillz", "life"], 2)


def test_plus_players_life_targets_both():
    assert parsed("+2 Players Life") == cap("both", ["life"], 2)


def test_plus_opp_pillz_targets_enemy():
    assert parsed("Defeat: +2 Opp. Pillz") == cap("enemy", ["pillz"], 2, conditions=["defeat"])


def test_opp_attack_plus_targets_enemy():
    assert parsed("Opp. Attack +4") == cap("enemy", ["attack"], 4)


def test_minus_opp_life_and_pillz():
    assert parsed("Vict. Or Def.: -2 Opp Life & Pillz Min 1") == cap("enemy", ["pillz", "life"], -2, borne=1, conditions=["victory_defeat"])


def test_minus_self_life_backlash():
    assert parsed("Backlash: - 2 Life Min 0") == cap("ally", ["life"], -2, borne=0, conditions=["backlash"])


def test_minus_players_pillz_targets_both():
    assert parsed("-1 Players Pillz. Min 2") == cap("both", ["pillz"], -1, borne=2)


# --- Préfixes ---------------------------------------------------------------------------------

@pytest.mark.parametrize("prefix, condition", [
    ("Courage", "courage"), ("Revenge", "revenge"), ("Confidence", "confidence"), ("Reprisal", "reprisal"),
    ("Symmetry", "symmetry"), ("Asymmetry", "asymmetry"), ("Defeat", "defeat"), ("Backlash", "backlash"),
    ("Victory Or Defeat", "victory_defeat"), ("Conf.", "confidence"),
])
def test_condition_prefixes(prefix, condition):
    assert parsed(f"{prefix}: Attack +5") == cap("ally", ["attack"], 5, conditions=[condition])


@pytest.mark.parametrize("prefix", ["Support", "Growth", "Degrowth", "Equalizer", "Brawl"])
def test_multiplier_prefixes(prefix):
    assert parsed(f"{prefix}: -1 Opp Attack, Min 3") == cap("enemy", ["attack"], -1, how=prefix.lower(), borne=3)


def test_condition_and_multiplier_combine():
    assert parsed("Defeat: Growth: -1 Opp. Life, Min 2") == cap("enemy", ["life"], -1, how="growth", borne=2, conditions=["defeat"])


def test_two_conditions_combine():
    assert parsed("Conf.: Vict. Or Def.: -3 Opp. Life, Min 2") == cap("enemy", ["life"], -3, borne=2, conditions=["confidence", "victory_defeat"])


@pytest.mark.parametrize("prefix", ["Stop", "Killshot", "Day", "Team", "Versus", "Xantiax"])
def test_unsupported_prefixes(prefix):
    result = parse_capacity(f"{prefix}: Power +2")

    assert (result.capacity, result.supported, result.reason) == (None, False, f"unsupported prefix: {prefix.lower()}")


def test_unknown_prefix():
    result = parse_capacity("Wibble: Power +2")

    assert (result.supported, result.reason) == (False, "unknown prefix: wibble")


# --- Suffixe « per » --------------------------------------------------------------------------

@pytest.mark.parametrize("suffix, how", [
    ("Pillz Left", "nb_pillz_left"), ("Life Left", "nb_life_left"),
    ("Life Lost", "nb_life_lost"), ("Pillz Lost", "nb_pillz_lost"), ("Opp. Damage", "nb_dam_opp"),
])
def test_per_multipliers(suffix, how):
    assert parsed(f"+1 Attack Per {suffix}") == cap("ally", ["attack"], 1, how=how)


def test_per_with_max():
    assert parsed("+1 Power Per Life Left Max. 9") == cap("ally", ["power"], 1, how="nb_life_left", borne=9)


def test_minus_opp_per_life_left():
    assert parsed("-4 Opp Att. Per Life Left, Min 2") == cap("enemy", ["attack"], -4, how="nb_life_left", borne=2)


@pytest.mark.parametrize("suffix", ["Damage", "Round", "Opp. Power"])
def test_unsupported_per_multipliers(suffix):
    result = parse_capacity(f"+1 Life Per {suffix}")

    assert (result.supported, result.reason) == (False, f"unsupported multiplier: per {normalize(suffix)}")


def test_prefix_and_per_multiplier_is_rejected():
    result = parse_capacity("Growth: +1 Attack Per Pillz Left")

    assert (result.supported, result.reason) == (False, "unsupported: two multipliers")
```

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: les nouveaux tests échouent avec `AssertionError: unknown core` (ou `reason` différente) ; les 20 de la Task 1 passent.

- [ ] **Step 3 : Implémenter** — remplacer la fin de `capacity_parser.py` (à partir de `def _unsupported`) par :

```python
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
```

- [ ] **Step 4 : Vérifier que tout passe**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: tous verts (≈ 60 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/core/parsing/capacity_parser.py tests/test_capacity_parser.py
git commit -m "feat(parseur): modificateurs de stats, préfixes conditions/multiplicateurs, suffixe per

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3 : Cœurs de niveau 1 (stop, copy, protection, cancel, exchange), niveau 4 (poison…), reanimate

**Files:**
- Modify: `src/core/parsing/capacity_parser.py`
- Test: `tests/test_capacity_parser.py`

**Interfaces:**
- Consumes: `_capacity`, `_unsupported`, `_types`, `_resolve_how`, `_parse_core` (Task 2).
- Produces: `parse_capacity` gère les formes #2 à #8 de la spec.

- [ ] **Step 1 : Écrire les tests rouges** (ajouter à `tests/test_capacity_parser.py`)

```python
# --- Niveau 1 : stop / copy / protection / cancel / exchange ---------------------------------

def test_stop_opp_bonus_golden():
    assert parsed("Stop Opp. Bonus") == cap("enemy", ["bonus"], 0, how="stop")


def test_stop_ability_without_opp():
    assert parsed("Confidence: Stop Ability") == cap("enemy", ["ability"], 0, how="stop", conditions=["confidence"])


@pytest.mark.parametrize("text, types", [
    ("Copy: Opp. Ability", ["ability"]), ("Copy: Opp. Bonus", ["bonus"]), ("Copy: Opp. Power", ["power"]),
    ("Copy: Opp. Damage", ["damage"]), ("Copy: Power And Damage Opp.", ["power", "damage"]),
    ("Reprisal: Copy Opp. Bonus", ["bonus"]),
])
def test_copy(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("enemy", types, "copy")


@pytest.mark.parametrize("text, types", [
    ("Protection: Ability", ["ability"]), ("Protection : Damage", ["damage"]), ("Protection: Attack", ["attack"]),
    ("Protection: Power And Damage", ["power", "damage"]), ("Courage: Bonus Protection", ["bonus"]),
    ("Courage: Prot.: Power & Damage", ["power", "damage"]), ("Revenge: Protec. Power And Dmg", ["power", "damage"]),
])
def test_protection(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("ally", types, "Protection")


@pytest.mark.parametrize("text, types", [
    ("Cancel Opp. Power Modif.", ["power"]), ("Cancel Opp. Pillz & Life Modif.", ["pillz", "life"]),
    ("Cancel Opp. Pow/dam Mod.", ["power", "damage"]), ("Reprisal: Cancel Opp Pow & Dam Mod", ["power", "damage"]),
])
def test_cancel(text, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["how"]) == ("enemy", types, "cancel")


@pytest.mark.parametrize("text, types", [
    ("Power Exchange", ["power"]), ("Damage Exchange", ["damage"]), ("Power And Damage Exchange", ["power", "damage"]),
])
def test_exchange(text, types):
    assert parsed(text) == cap("both", types, 0, how="exchange")


# --- Niveau 4 : effets persistants ------------------------------------------------------------

@pytest.mark.parametrize("text, target, types", [
    ("Poison 2, Min 1", "enemy", ["poison"]), ("Toxin 1, Min 3", "enemy", ["toxine"]),
    ("Heal 2 Max. 10", "ally", ["heal"]), ("Regen 1, Max. 12", "ally", ["regen"]), ("Dope 1, Max. 8", "ally", ["dope"]),
])
def test_persistent_effects(text, target, types):
    result = parsed(text)

    assert (result["target"], result["types"], result["value"], result["borne"]) == (target, types, int(text.split()[1].rstrip(",")), int(text.split()[-1]))


def test_growth_poison_keeps_multiplier():
    assert parsed("Growth: Poison 1, Min 2") == cap("enemy", ["poison"], 1, how="growth", borne=2)


# --- Reanimate --------------------------------------------------------------------------------

def test_reanimate_golden():
    assert parsed("Support: Reanimate: +1 Life") == cap("ally", ["reanimate"], 1, how="support")
```

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: nouveaux tests en échec (`unknown core`), anciens verts.

- [ ] **Step 3 : Implémenter** — ajouter les regex après `_R_MINUS_SELF` et étendre `_parse_core` :

```python
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
```

et, au début de `_parse_core` (avant `_R_STAT_PLUS`) :

```python
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
```

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: tous verts.

- [ ] **Step 5 : Commit**

```bash
git add src/core/parsing/capacity_parser.py tests/test_capacity_parser.py
git commit -m "feat(parseur): stop, copy, protection, cancel, exchange, effets persistants, reanimate

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4 : Cœurs explicitement non supportés + repository des cartes + test de couverture

**Files:**
- Create: `src/adapters/repositories/card_repository.py`
- Modify: `src/core/parsing/capacity_parser.py`
- Test: `tests/test_capacity_parser.py`

**Interfaces:**
- Produces: `get_official_card(card_name: str) -> tuple[str, dict]` (nom canonique, données brutes ; `ValueError` si inconnue) ; `all_capacity_descriptions() -> set[str]` (bonus + abilities de tous les niveaux, strippées).

- [ ] **Step 1 : Écrire les tests rouges** (ajouter à `tests/test_capacity_parser.py`)

```python
from src.adapters.repositories.card_repository import all_capacity_descriptions


@pytest.mark.parametrize("text, keyword", [
    ("-2 Cards Damage, Min 1", "cards"), ("Protection: Cards Power And Damage", "cards"),
    ("Damage Impose", "impose"), ("Cancel Leader", "cancel leader"), ("Consume 2, Min 1", "consume"),
    ("Corrupt 2 Min. 1", "corrupt"), ("Victory Or Defeat: Combust 2, Min 1", "combust"),
    ("Victory Or Defeat: Corrosion 1, Min 2", "corrosion"), ("Revenge: Mindwipe 2, Min 1", "mindwipe"),
    ("Rebirth 2, Max. 10", "rebirth"), ("Recover 2 Pillz Out Of 3", "recover"),
    ("Remove Ability Conditions", "remove ability conditions"), ("Beyond", "beyond"), ("Tie-break", "tie-break"),
    ("Counter-attack", "counter-attack"), ("Limitless", "limitless"),
])
def test_explicitly_unsupported_cores(text, keyword):
    result = parse_capacity(text)

    assert (result.capacity, result.supported, result.reason) == (None, False, f"unsupported core: {keyword}")


def test_gibberish_is_unknown_core():
    assert parse_capacity("Blorp the flurb").reason == "unknown core"


# --- Couverture sur les 906 descriptions officielles -----------------------------------------

SUPPORTED_DESCRIPTIONS_FLOOR = 0  # à remplacer par la valeur mesurée (Step 4)


def test_every_official_description_parses_without_raising():
    descriptions = all_capacity_descriptions()
    results = {text: parse_capacity(text) for text in descriptions}   # ne doit pas lever

    assert len(descriptions) == 906
    assert all(r.reason for r in results.values() if not r.supported)
    supported = sum(1 for r in results.values() if r.supported)
    assert supported >= SUPPORTED_DESCRIPTIONS_FLOOR, f"couverture en baisse : {supported} < {SUPPORTED_DESCRIPTIONS_FLOOR}"
```

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: `ModuleNotFoundError` sur `card_repository` ; après création du module, les cas « unsupported core » échouent avec `unknown core`.

- [ ] **Step 3 : Implémenter**

```python
# src/adapters/repositories/card_repository.py
"""Accès en lecture aux cartes officielles scrapées (data/jsonData_officiel.json), chargées une seule fois."""
import json
import os
from functools import lru_cache
from typing import Dict, Set, Tuple

from src.utils.config import BASE_DIR

OFFICIAL_CARDS_PATH = os.path.join(BASE_DIR, "data", "jsonData_officiel.json")


@lru_cache(maxsize=1)
def _official_cards() -> Dict[str, dict]:
    with open(OFFICIAL_CARDS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_official_card(card_name: str) -> Tuple[str, dict]:
    """Retourne (nom canonique, données brutes) ; recherche insensible à la casse."""
    wanted = card_name.lower()
    for name, data in _official_cards().items():
        if name.lower() == wanted:
            return name, data
    raise ValueError(f"No card found with name: {card_name}")


def all_capacity_descriptions() -> Set[str]:
    """Toutes les descriptions distinctes de bonus et d'abilities (tous niveaux d'étoiles)."""
    descriptions = set()
    for data in _official_cards().values():
        descriptions.add(data.get("bonus", "").strip())
        for level, star_data in data.items():
            if level.isdigit():
                descriptions.add(star_data.get("ability", "").strip())
    return descriptions
```

Dans `capacity_parser.py`, ajouter après `_CORE_STARTERS` :

```python
# Cœurs connus mais hors moteur : testés avant les regex, raison groupable dans le rapport
_UNSUPPORTED_CORE_KEYWORDS = (
    "remove ability conditions", "cancel leader", "counter-attack", "tie-break",
    "cards", "impose", "consume", "corrupt", "combust", "corrosion", "mindwipe", "rebirth", "recover",
    "beyond", "bypass", "hazard", "illusion", "infiltrated", "limitless",
)
```

et au tout début de `_parse_core` (avant la ligne `how, error = _resolve_how(prefix_hows, None)`) :

```python
    for keyword in _UNSUPPORTED_CORE_KEYWORDS:
        if re.search(rf"(?<![\w-]){re.escape(keyword)}(?![\w-])", core):
            return _unsupported(f"unsupported core: {keyword}")
```

- [ ] **Step 4 : Mesurer la couverture et pinner le plancher**

Run : `python -c "from src.adapters.repositories.card_repository import all_capacity_descriptions as a; from src.core.parsing.capacity_parser import parse_capacity as p; d=a(); print(sum(p(x).supported for x in d), '/', len(d))"`
Remplacer `SUPPORTED_DESCRIPTIONS_FLOOR = 0` par la valeur affichée. Si elle est inférieure à ~55 % de 906, lister les `unknown core` (voir Task 8, script) et vérifier qu'il ne s'agit pas d'une regex trop stricte avant de pinner.

- [ ] **Step 5 : Vérifier**

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py`
Expected: tous verts.

- [ ] **Step 6 : Commit**

```bash
git add src/core/parsing/capacity_parser.py src/adapters/repositories/card_repository.py tests/test_capacity_parser.py
git commit -m "feat(parseur): cœurs hors moteur explicites, repository des cartes officielles, test de couverture

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5 : `Card` chargée depuis le repository + parseur ; suppression de la chaîne `from_dict`

**Files:**
- Modify: `src/core/domain/card.py` (tout `__init__`, `from_dict_template`, suppression de `from_dict`), `src/core/domain/player.py` (suppression de `from_dict`), `src/core/domain/game.py` (suppression de `from_dict`)
- Test: `tests/test_card_loading.py`

**Interfaces:**
- Consumes: `get_official_card` (Task 4), `parse_capacity` (Tasks 1-4).
- Produces: `Card(card_name: str, nb_stars: int)` avec `ability`/`bonus` de type `Capacity | None`, `ability_description`/`bonus_description` de type `str`, `power`/`damage` `int`.

- [ ] **Step 1 : Écrire les tests rouges**

```python
# tests/test_card_loading.py
import pytest

from src.core.domain.card import Card
from src.core.domain.capacity import Capacity


def test_card_is_built_from_official_data_with_parsed_capacities():
    card = Card("Aamir", 3)

    assert (card.name, card.faction, card.stars, card.starOff) == ("Aamir", "All Stars", 3, 3)
    assert (card.power, card.damage) == (5, 4)                      # "5 " / "4 " dans le JSON
    assert (card.ability_description, card.bonus_description) == ("Growth: -1 Opp Power, Min 4", "-2 Opp Power, Min 1")
    assert card.ability.to_dict() == Capacity("enemy", ["power"], -1, 4, how="growth").to_dict()
    assert card.bonus.to_dict() == Capacity("enemy", ["power"], -2, 1).to_dict()
    assert (card.power_fight, card.damage_fight, card.pillz_fight, card.attack) == (0, 0, 0, 0)
    assert (card.ability_fight, card.bonus_fight, card.fury, card.played, card.win) == (None, None, False, False, False)


def test_card_name_lookup_is_case_insensitive():
    assert Card("aamir", 3).name == "Aamir"


def test_unknown_card_raises():
    with pytest.raises(ValueError, match="No card found"):
        Card("Zorglub", 1)


def test_missing_star_level_raises():
    with pytest.raises(ValueError, match="No data for 5 stars"):
        Card("Aamir", 5)


def test_ability_locked_at_lower_level_is_none():
    card = Card("Aamir", 1)

    assert (card.ability, card.ability_description) == (None, "Ability at Level 3")


def test_unsupported_ability_is_none_but_description_is_kept():
    card = Card("Raoul", 2)   # "Killshot: +5 Life" : préfixe hors moteur

    assert card.ability is None
    assert card.ability_description == "Killshot: +5 Life"


def test_card_with_no_ability_round_trips_through_json():
    card = Card("Aamir", 1)

    restored = Card.from_dict_template(card.to_dict())

    assert restored.ability is None
    assert restored.to_dict() == card.to_dict()
```

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_card_loading.py`
Expected: `FileNotFoundError: JSON file not found at path: ../data/jsonData_officiel.json` (chemin relatif au CWD).

- [ ] **Step 3 : Implémenter** — réécrire `card.py` (conserver CRLF) :

```python
# src/core/domain/card.py
from src.adapters.repositories.card_repository import get_official_card
from src.core.domain.capacity import Capacity
from src.core.parsing.capacity_parser import parse_capacity


class Card:

    def __init__(self, card_name: str, nb_stars: int = 1):
        """
        Initialise une carte à partir de son nom et de son nombre d'étoiles (données officielles scrapées).
        Les abilities / bonus sont parsés en Capacity ; None si absents ou non gérés par le moteur.
        """
        name, card_data = get_official_card(card_name)
        star_data = card_data.get(str(nb_stars))
        if not star_data:
            raise ValueError(f"No data for {nb_stars} stars for card: {card_name}")

        self.name: str = name
        self.faction: str = card_data.get("faction", "")
        self.starOff: int = card_data.get("starOff", 0)
        self.stars: int = nb_stars
        self.power: int = int(str(star_data.get("power", 0)).strip())
        self.damage: int = int(str(star_data.get("damage", 0)).strip())

        self.bonus_description: str = card_data.get("bonus", "").strip()
        self.ability_description: str = star_data.get("ability", "").strip()
        self.bonus: Capacity = parse_capacity(self.bonus_description).capacity
        self.ability: Capacity = parse_capacity(self.ability_description).capacity

        self.power_fight: int = 0
        self.damage_fight: int = 0
        self.ability_fight: Capacity = None
        self.bonus_fight: Capacity = None
        self.pillz_fight: int = 0
        self.fury: bool = False

        self.attack: int = 0
        self.played: bool = False
        self.win: bool = False

    @staticmethod
    def from_dict_template(data: dict) -> "Card":

        card = Card.__new__(Card)
        card.name = data.get("name")
        card.faction = data.get("faction")
        card.starOff = data.get("starOff")
        card.bonus = Capacity.from_dict(data["bonus"]) if data.get("bonus") else None
        card.stars = data.get("stars")
        card.power = data.get("power")
        card.damage = data.get("damage")
        card.ability = Capacity.from_dict(data["ability"]) if data.get("ability") else None

        card.bonus_description = data.get("bonus_description")
        card.ability_description = data.get("ability_description")

        card.pillz_fight = data.get("pillz_fight")
        card.fury = data.get("fury", False)
        card.attack = data.get("attack")
        card.played = data.get("played")

        card.power_fight = data.get("power_fight")
        card.damage_fight = data.get("damage_fight")
        card.ability_fight = Capacity.from_dict(data.get("ability_fight")) if data.get("ability_fight") else None
        card.bonus_fight = Capacity.from_dict(data.get("bonus_fight")) if data.get("bonus_fight") else None
        card.win = data.get("win")
        return card

    def to_dict(self) -> dict:
        """
        Convertit la carte en dictionnaire JSON-serializable.
        """
        return {
            "name": self.name,
            "faction": self.faction,
            "starOff": self.starOff,
            "bonus": self.bonus.to_dict() if self.bonus else None,
            "stars": self.stars,
            "power": self.power,
            "damage": self.damage,
            "ability": self.ability.to_dict() if self.ability else None,
            "bonus_description": self.bonus_description,
            "ability_description": self.ability_description,
            "pillz_fight": self.pillz_fight,
            "fury": self.fury,
            "attack": self.attack,
            "played": self.played,
            "power_fight": self.power_fight,
            "damage_fight": self.damage_fight,
            "ability_fight": self.ability_fight.to_dict() if self.ability_fight else None,
            "bonus_fight": self.bonus_fight.to_dict() if self.bonus_fight else None,
            "win": self.win,
        }

    # print les données de fight + attack
    def __repr__(self) -> str:
        return f"Card(name={self.name}, power_fight={self.power_fight}, damage_fight={self.damage_fight}, attack={self.attack}, played={self.played}, win={self.win})"
```

Dans `player.py` : supprimer la méthode `from_dict` (lignes `@staticmethod def from_dict(data)` … `return player`), garder `from_dict_template`.
Dans `game.py` : supprimer la méthode `from_dict` ; garder `from_dict_template`.

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest -q -p no:warnings`
Expected: tous verts (les 42 anciens + parseur + chargement). `grep -rn "from_dict(" src main.py | grep -v "from_dict_template\|Capacity.from_dict\|Round(\*\*"` ne renvoie rien.

- [ ] **Step 5 : Commit**

```bash
git add src/core/domain/card.py src/core/domain/player.py src/core/domain/game.py tests/test_card_loading.py
git commit -m "feat(cartes): Card chargée depuis le JSON officiel via BASE_DIR, abilities/bonus parsés en Capacity

Suppression de la chaîne morte Game.from_dict -> Player.from_dict -> Card.from_dict ;
from_dict_template tolère ability/bonus null.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6 : Garde-fous du moteur — `check_capacity_condition` (None, conditions différées) sur la copie de combat

**Files:**
- Modify: `src/core/use_cases/process_round.py` (appels lignes ~29-36 ; fonction `check_capacity_condition` en entier)
- Create: `scripts/regenerate_example_fixtures.py`
- Modify: `data/test/test_1..3` (régénérées)
- Test: `tests/test_process_round.py`

**Interfaces:**
- Consumes: `_bet_threshold(bet: str) -> int` (existant).
- Produces: `check_capacity_condition(game, capacity: Capacity | None, is_ally, own_card_index, opp_card_index) -> bool` ; constante `DEFERRED_CONDITIONS = {"defeat", "backlash", "victory_defeat"}`.

- [ ] **Step 1 : Écrire les tests rouges** (ajouter à `tests/test_process_round.py`)

```python
from src.core.use_cases.process_round import DEFERRED_CONDITIONS, process_round
from src.schemas.game_schemas import ProcessRoundInput


def test_none_capacity_has_no_condition_to_check(template_game):
    assert check_capacity_condition(template_game, None, True, 0, 0) is True


def test_deferred_condition_is_left_for_level_3(template_game):
    capacity = Capacity(target="enemy", types=["life"], value=-2, borne=0, effect_conditions=["defeat"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True
    assert capacity.effect_conditions == ["defeat"]


def test_met_condition_is_consumed_and_deferred_one_kept(template_game):
    template_game.turn = True
    capacity = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["courage", "defeat"])

    assert check_capacity_condition(template_game, capacity, True, 0, 0) is True
    assert capacity.effect_conditions == ["defeat"]


def test_unknown_condition_raises(template_game):
    capacity = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["moonlight"])

    with pytest.raises(ValueError, match="Invalid effect_conditions"):
        check_capacity_condition(template_game, capacity, True, 0, 0)


def test_deferred_conditions_constant():
    assert DEFERRED_CONDITIONS == {"defeat", "backlash", "victory_defeat"}


def test_courage_life_ability_applies_and_leaves_the_original_untouched(template_game):
    # Allison reçoit "Courage: +2 Life" (capacité de niveau 3 avec condition de début de round)
    template_game.turn = True
    allison = template_game.ally.cards[1]
    allison.ability = Capacity(target="ally", types=["life"], value=2, borne=-1, effect_conditions=["courage"])
    round_data = ProcessRoundInput(player1_card_index=1, player1_pillz=4, player2_card_index=2, player2_pillz=1)

    process_round(template_game, round_data)   # Allison (5-2)x4 = 12 > Bhudd 4x1 = 4 : victoire

    assert allison.win is True
    assert template_game.ally.life == 14
    assert allison.ability.effect_conditions == ["courage"]
```

(`Capacity`, `check_capacity_condition`, `pytest` sont déjà importés en tête du fichier ; ajouter `import pytest` s'il manque.)

- [ ] **Step 2 : Vérifier qu'ils échouent**

Run: `python -m pytest -q -p no:warnings tests/test_process_round.py`
Expected: `AttributeError: 'NoneType' object has no attribute 'effect_conditions'`, `ValueError: Invalid effect_conditions … ['defeat']`, `ImportError: DEFERRED_CONDITIONS`, et pour le dernier `ValueError` levée au niveau 3 (`check_capacity_condition_lvl_3`).

- [ ] **Step 3 : Implémenter** — dans `process_round.py` :

Remplacer les 4 appels (lignes ~29-36) :

```python
        if not check_capacity_condition(game, player1_card.ability_fight, True, round_data.player1_card_index, round_data.player2_card_index):
            player1_card.ability_fight = None
        if not check_capacity_condition(game, player1_card.bonus_fight, True, round_data.player1_card_index, round_data.player2_card_index):
            player1_card.bonus_fight = None
        if not check_capacity_condition(game, player2_card.ability_fight, False, round_data.player2_card_index, round_data.player1_card_index):
            player2_card.ability_fight = None
        if not check_capacity_condition(game, player2_card.bonus_fight, False, round_data.player2_card_index, round_data.player1_card_index):
            player2_card.bonus_fight = None
```

Remplacer toute la fonction `check_capacity_condition` (jusqu'à `_find_bet_condition` exclu) par :

```python
DEFERRED_CONDITIONS = {"defeat", "backlash", "victory_defeat"}  # évaluées après le combat (niveau 3)


def check_capacity_condition(game: Game, capacity: Capacity, is_ally: bool, own_card_index: int, opp_card_index: int) -> bool:
    """
    Vérifie (et consomme) les conditions de début de round d'une capacité de combat.
    own_card_index / opp_card_index : index de la carte jouée par le joueur qui possède la capacité / par son adversaire.
    Retourne False si une condition n'est pas remplie ; les conditions différées au niveau 3 sont laissées en place.
    """
    if capacity is None or not capacity.effect_conditions:
        return True

    own_player = game.ally if is_ally else game.enemy
    last_round = game.history[-1] if game.history else None
    own_won_last_round = None if last_round is None else (last_round.ally.win if is_ally else last_round.enemy.win)
    plays_first = game.turn if is_ally else not game.turn

    checks = {
        "revenge": lambda: own_won_last_round is False,
        "confidence": lambda: own_won_last_round is True,
        "courage": lambda: plays_first,
        "reprisal": lambda: not plays_first,
        "symmetry": lambda: own_card_index == opp_card_index,
        "asymmetry": lambda: own_card_index != opp_card_index,
    }

    for condition in list(capacity.effect_conditions):
        if condition in checks:
            if not checks[condition]():
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("bet"):
            if own_player.cards[own_card_index].pillz_fight <= _bet_threshold(condition):
                return False
            capacity.effect_conditions.remove(condition)
        elif condition not in DEFERRED_CONDITIONS:
            raise ValueError(f"Invalid effect_conditions (check_capacity_condition): {capacity.effect_conditions}")
    return True
```

Supprimer `_find_bet_condition` (plus utilisée) ; garder `_bet_threshold`.

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest -q -p no:warnings`
Expected: tout vert **sauf** `test_fixtures_replay[test_2]` : la fixture a été générée quand `ability.effect_conditions` d'Allison était vidée sur l'original (`[]` dans `curr`) ; l'original n'étant plus muté, le rejeu produit `["courage"]`. Les fixtures doivent être régénérées avec le mécanisme réel (Step 5).

- [ ] **Step 5 : Script de régénération des fixtures d'exemple**

```python
# scripts/regenerate_example_fixtures.py
"""
Régénère les fixtures d'exemple data/test/test_1..3 par le mécanisme réel (API + /save_for_test) dans un
bac à sable, puis les copie dans data/test. À relancer quand le format de partie ou le template change.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/regenerate_example_fixtures.py
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import src.core.services.game_service as game_service  # noqa: E402
from src.utils.config import BASE_DIR  # noqa: E402

# (index allié, index ennemi, pillz allié, pillz ennemi, fury allié, fury ennemi) — résultats vérifiés à la main
PLAYS = [
    (2, 2, 3, 3, False, False),  # Amelia vs Bhudd (stop bonus)         -> ennemi 12 -> 7
    (1, 0, 2, 2, False, False),  # Allison vs Asporov (support)         -> allié 12 -> 6
    (0, 1, 2, 2, True, False),   # Agustino fury vs B Mappe (equalizer) -> ennemi 7 -> 4, pillz 9 -> 5
]


def main() -> None:
    sandbox = tempfile.mkdtemp(prefix="urban_fixtures_")
    os.makedirs(os.path.join(sandbox, "data"))
    shutil.copy(os.path.join(BASE_DIR, "data", "template_game_v1.json"), os.path.join(sandbox, "data"))
    game_service.BASE_DIR = sandbox
    os.chdir(sandbox)

    from fastapi.testclient import TestClient  # noqa: E402
    from main import app  # noqa: E402

    client = TestClient(app)
    game_id = client.get("/init_game/template").json()["game_id"]
    for ally, enemy, ally_pillz, enemy_pillz, ally_fury, enemy_fury in PLAYS:
        played = client.post(f"/process_round/{game_id}", json={
            "player1_card_index": ally, "player1_pillz": ally_pillz, "player1_fury": ally_fury,
            "player2_card_index": enemy, "player2_pillz": enemy_pillz, "player2_fury": enemy_fury,
        })
        assert played.status_code == 200, played.json()
        saved = client.get("/save_for_test", params={"game_id": game_id})
        assert saved.status_code == 200, saved.json()

    target = os.path.join(BASE_DIR, "data", "test")
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(os.path.join(sandbox, "data", "test"), target)
    print(f"{len(PLAYS)} fixtures régénérées dans {target}")


if __name__ == "__main__":
    main()
```

Run : `python scripts/regenerate_example_fixtures.py 2>&1 | tail -1` puis `python -m pytest -q -p no:warnings`
Expected: `3 fixtures régénérées …` ; suite entièrement verte. Vérifier avec `git diff --stat data/test` que seuls `effect_conditions` d'Allison (test_2) et l'ordre/valeurs attendues changent.

- [ ] **Step 6 : Commit**

```bash
git add src/core/use_cases/process_round.py tests/test_process_round.py scripts/regenerate_example_fixtures.py data/test
git commit -m "fix(moteur): conditions vérifiées sur la copie de combat, capacité None tolérée, conditions différées au niveau 3

Les fixtures d'exemple sont régénérées (l'original ability n'est plus muté) par
scripts/regenerate_example_fixtures.py, qui rejoue les 3 coups validés via l'API.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7 : `POST /init_game/` jouable — `create_game` renvoie l'id, `nb_turn = 1`

**Files:**
- Modify: `src/core/services/game_service.py` (`create_game`), `main.py` (`init_game`)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `Card(card_name, nb_stars)` (Task 5).
- Produces: `create_game(players_cards: PlayerCards) -> tuple[Game, int]` ; réponse `POST /init_game/` = `{"status", "game", "game_id"}`.

- [ ] **Step 1 : Écrire le test rouge** (ajouter à `tests/test_api.py`)

```python
REAL_DECK = {
    "player1": [{"card_name": "Aamir", "nb_stars": 3}, {"card_name": "Allison", "nb_stars": 3},
                {"card_name": "Amelia", "nb_stars": 3}, {"card_name": "Ashley", "nb_stars": 2}],
    "player2": [{"card_name": "Asporov", "nb_stars": 4}, {"card_name": "B Mappe Mt", "nb_stars": 5},
                {"card_name": "Bhudd", "nb_stars": 3}, {"card_name": "Serafina", "nb_stars": 5}],
}


def test_init_game_with_real_cards_then_play_a_round(client):
    response = client.post("/init_game/", json=REAL_DECK)

    assert response.status_code == 200, response.json()
    body = response.json()
    game_id = body["game_id"]
    assert body["game"]["nb_turn"] == 1
    aamir = body["game"]["ally"]["cards"][0]
    assert (aamir["power"], aamir["damage"], aamir["ability"]["how"]) == (5, 4, "growth")

    played = _play(client, game_id, 0, 2)   # Aamir vs Bhudd

    assert played.status_code == 200, played.json()
    assert played.json()["game"]["nb_turn"] == 2
```

- [ ] **Step 2 : Vérifier qu'il échoue**

Run: `python -m pytest -q -p no:warnings tests/test_api.py`
Expected: `KeyError: 'game_id'`.

- [ ] **Step 3 : Implémenter**

Dans `game_service.py`, `create_game` :

```python
def create_game(players_cards: PlayerCards):
    """
    Crée une partie en initialisant les joueurs avec leurs cartes.

    Args:
        players_cards (PlayerCards): Objet contenant les cartes de `player1` et `player2`.

    Returns:
        (Game, int): la partie initialisée (round 1 en cours) et son identifiant.
    """
    game = Game(1, True, Player(name="ally", life=12, pillz=12), Player(name="enemy", life=12, pillz=12), [])

    # Ajouter les cartes à player1
    for card_input in players_cards.player1:
        card = Card(card_name=card_input.card_name, nb_stars=card_input.nb_stars)
        game.ally.cards.append(card)

    # Ajouter les cartes à player2
    for card_input in players_cards.player2:
        card = Card(card_name=card_input.card_name, nb_stars=card_input.nb_stars)
        game.enemy.cards.append(card)

    new_id = get_new_game_id()

    # Créer un dossier spécifique pour cette partie
    game_directory = os.path.join("data", "game", f"game_{new_id}")
    os.makedirs(game_directory, exist_ok=True)

    # Appeler la fonction pour sauvegarder la partie en JSON dans le dossier créé
    save_game_to_json(game, new_id, game_directory)

    return (game, new_id)
```

Dans `main.py`, `init_game` :

```python
        # Créer une partie avec les données validées
        (game, new_id) = create_game(players_cards)

        # Retourner la partie initialisée
        return {"status": "success", "game": game.to_dict(), "game_id": new_id}
```

et faire remonter les erreurs métier en 400 : dans le même `try`, ajouter avant le `except Exception` :

```python
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest -q -p no:warnings`
Expected: tous verts.

- [ ] **Step 5 : Commit**

```bash
git add src/core/services/game_service.py main.py tests/test_api.py
git commit -m "feat(api): POST /init_game/ renvoie game_id et démarre au round 1 ; cartes inconnues -> 400

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8 : Script de couverture + template corrigé + push

**Files:**
- Create: `scripts/capacity_coverage.py`
- Modify: `data/template_game_v1.json` (`Bhudd` → `ability.value` 5 → 0)

**Interfaces:**
- Consumes: `all_capacity_descriptions`, `parse_capacity`.

- [ ] **Step 1 : Ajouter le golden « Stop » complet** (dans `tests/test_capacity_parser.py`, la liste de `test_golden_template_encodings`) :

```python
    ("Stop Opp. Bonus", cap("enemy", ["bonus"], 0, how="stop")),
    ("Support: Reanimate: +1 Life", cap("ally", ["reanimate"], 1, how="support")),
```

puis un test qui confronte le template au parseur :

```python
def test_template_capacities_match_the_parser(template_data):
    for side in ("ally", "enemy"):
        for card in template_data[side]["cards"]:
            assert parse_capacity(card["ability_description"]).capacity.to_dict() == card["ability"], card["name"]
            assert parse_capacity(card["bonus_description"]).capacity.to_dict() == card["bonus"], card["name"]
```

Run: `python -m pytest -q -p no:warnings tests/test_capacity_parser.py -k template`
Expected: échec sur `Bhudd` (`value` 0 ≠ 5).

- [ ] **Step 2 : Corriger le template** — dans `data/template_game_v1.json`, carte `Bhudd`, bloc `"ability"` : `"value": 5` → `"value": 0`. Relancer le test : vert. Lancer `python -m pytest -q -p no:warnings` : le rejeu des fixtures reste vert (elles embarquent leur propre copie du template).

- [ ] **Step 3 : Écrire le script**

```python
# scripts/capacity_coverage.py
"""
Rapport de couverture du parseur de capacités sur les descriptions officielles.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/capacity_coverage.py
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.repositories.card_repository import all_capacity_descriptions  # noqa: E402
from src.core.parsing.capacity_parser import parse_capacity  # noqa: E402


def main() -> None:
    descriptions = sorted(all_capacity_descriptions())
    results = {text: parse_capacity(text) for text in descriptions}
    supported = [text for text, result in results.items() if result.supported]
    unsupported = defaultdict(list)
    for text, result in results.items():
        if not result.supported:
            unsupported[result.reason].append(text)

    print(f"{len(supported)}/{len(descriptions)} descriptions supportées ({100 * len(supported) / len(descriptions):.1f} %)")
    print(f"{len(descriptions) - len(supported)} non supportées, par raison :")
    for reason, count in Counter({reason: len(texts) for reason, texts in unsupported.items()}).most_common():
        print(f"\n[{count}] {reason}")
        for text in sorted(unsupported[reason]):
            print(f"    {text}")


if __name__ == "__main__":
    main()
```

Run: `python scripts/capacity_coverage.py | head -30` — vérifier que la première ligne affiche le même nombre que `SUPPORTED_DESCRIPTIONS_FLOOR`.

- [ ] **Step 4 : Suite complète et commit**

Run: `python -m pytest -q -p no:warnings`
Expected: tous verts.

```bash
git add scripts/capacity_coverage.py data/template_game_v1.json tests/test_capacity_parser.py
git commit -m "feat: rapport de couverture du parseur + template aligné sur le parseur (Stop value 0)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
```

- [ ] **Step 5 : Reporter à l'utilisateur** : couverture mesurée (N/906), les 5 raisons les plus fréquentes, et confirmation que `/init_game/` joue un round avec de vraies cartes.
