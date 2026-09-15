# Parseur de capacités `description → Capacity` — design

Date : 2026-09-15 · Branche : `fix/bugs-moteur-et-fixtures` (suite du point 4 du rapport d'état)

## 1. Objectif

Rendre les 2 160 cartes de `data/jsonData_officiel.json` jouables : leurs abilities et bonus n'existent
aujourd'hui que sous forme de texte (`"Growth: -1 Opp Power, Min 4"`), seules les 8 cartes du template
ont une capacité structurée écrite à la main. On écrit un parseur qui produit un objet `Capacity` à partir
du texte, on l'intègre au chargement des cartes (`Card(name, stars)`), ce qui répare `/init_game/`.

Décision prise avec l'utilisateur : **une capacité que le moteur ne sait pas jouer rend la carte jouable
avec une capacité inerte** (`None`), jamais une erreur. Un rapport de couverture liste ce qui manque.

Hors périmètre : corriger les niveaux 3 et 4 du moteur (bugs #8, #10 du rapport), le front, le rescraping.

## 2. Vocabulaire cible = celui du moteur

Le parseur doit produire exactement les valeurs que les quatre niveaux du moteur reconnaissent :

| Champ `Capacity` | Valeurs attendues |
|---|---|
| `target` | `ally`, `enemy`, `both` |
| `types` | niveau 1-2 : `power`, `damage`, `attack`, `ability`, `bonus` · niveau 3 : `life`, `pillz`, `reanimate` · niveau 4 : `poison`, `toxine`, `heal`, `regen`, `dope` |
| `how` | multiplicateurs : `""`, `support`, `growth`, `degrowth`, `equalizer`, `brawl`, `nb_pillz_left`, `nb_life_left`, `nb_life_lost`, `nb_pillz_lost`, `nb_dam_opp` · niveau 1 : `stop`, `copy`, `Protection` (majuscule, tel quel dans le moteur), `cancel`, `exchange` |
| `value` | entier signé (`-2` pour `-2 Opp Power`, `+3` pour `Damage +3`, `0` pour stop/copy/…) |
| `borne` | `Min Y` / `Max Y` → `Y` ; sinon `-1` |
| `effect_conditions` | liste parmi `courage`, `revenge`, `confidence`, `reprisal`, `symmetry`, `asymmetry` (évaluées au début du round), `defeat`, `backlash`, `victory_defeat` (différées au niveau 3) |
| `lvl_priority` | toujours `0` |

**`supported` signifie « le vocabulaire est celui du moteur »**, pas « le moteur applique correctement
l'effet ». Poison/heal/dope s'encodent (vocabulaire du niveau 4) bien que le niveau 4 soit bugué.

## 3. Le parseur — `src/core/parsing/capacity_parser.py`

### Interface

```python
@dataclass(frozen=True)
class ParsedCapacity:
    capacity: Capacity | None   # None si pas d'ability à ce niveau OU non supporté
    supported: bool             # False => capacity est None et reason explique pourquoi
    reason: str                 # "" si supporté ; sinon ex. "unsupported prefix: killshot"

def parse_capacity(text: str) -> ParsedCapacity
```

Fonction pure, déterministe, **ne lève jamais d'exception** quel que soit le texte. Texte vide,
`No Ability`, `Ability at Level N` → `ParsedCapacity(None, supported=True, reason="no ability")`.

### Pipeline

1. **Normalisation** du texte : minuscules ; `&` → ` and ` ; `;` → `:` ; `pow/dam` → `power and damage` ;
   synonymes mot à mot (point final optionnel) : `pow`→`power`, `dam`/`dmg`→`damage`, `atk`/`att`→`attack`,
   `opp.`→`opp`, `min.`→`min`, `max.`→`max`, `modif.`/`mod`→`modif`, `prot.`/`protec.`/`protect.`→`protection`,
   `canc.`→`cancel`, `rec.`→`recover`, `conf.`→`confidence`, `vict.`→`victory`, `def.`→`defeat` ;
   `- X` → `-X`, `+ X` → `+X` ; suppression des virgules et des points restants ; `-X pillz opp` → `-X opp pillz` ;
   espaces multiples réduits, espaces avant `:` supprimés.
2. **Découpage préfixes / cœur** sur `:` : on consomme de gauche à droite tant que le segment est un préfixe
   connu ; le reste (rejoint par `:`) est le cœur. Ainsi `courage: copy: opp bonus` → préfixes `[courage]`,
   cœur `copy: opp bonus`.
3. **Préfixes** :
   - conditions → `effect_conditions` : `courage`, `revenge`, `confidence`, `reprisal`, `symmetry`, `asymmetry`,
     `defeat`, `backlash`, `victory or defeat` → `victory_defeat` ;
   - multiplicateurs → `how` : `support`, `growth`, `degrowth`, `equalizer`, `brawl` ;
   - non supportés (raison `unsupported prefix: <x>`) : `stop`, `killshot`, `day`, `team`, `versus` ;
   - inconnu → `unknown prefix: <x>`.
   Deux multiplicateurs (préfixe + suffixe `per …`, ou deux préfixes) → `unsupported: two multipliers`.
4. **Cœur** — première regex qui matche, sur le texte normalisé :

| # | Cœur | Encodage |
|---|---|---|
| 1 | `no ability`, `ability at level N` | `None`, supporté |
| 2 | `stop (opp )?(ability\|bonus)` | enemy, `[ability\|bonus]`, how `stop` |
| 3 | `copy:? (opp )?(ability\|bonus\|power\|damage\|power and damage)( opp)?` | enemy, types, how `copy` |
| 4 | `protection:? (ability\|bonus\|power\|damage\|attack\|power and damage)` et `(ability\|bonus) protection` | ally, types, how `Protection` |
| 5 | `cancel opp (power\|damage\|attack\|life\|pillz\|power and damage\|pillz and life) modif` | enemy, types, how `cancel` |
| 6 | `(power\|damage\|power and damage) exchange` | both, types, how `exchange` |
| 7 | `(poison\|toxin\|heal\|regen\|dope) X (min\|max) Y` | `[poison]`/`[toxine]`/`[heal]`/`[regen]`/`[dope]`, value `X`, borne `Y` ; target enemy pour poison/toxin, ally sinon |
| 8 | `reanimate:? +X life` | ally, `[reanimate]`, value `X` |
| 9 | `(power\|damage\|attack\|power and damage) +X( max Y)?` | ally, types, `+X`, borne `Y`/`-1` |
| 10 | `+X (life\|pillz\|attack\|power\|damage\|pillz and life)( per M)?( max Y)?` | ally ; `+X players (life\|pillz)` → both ; `+X opp (life\|pillz\|attack)` → enemy |
| 11 | `-X opp (power\|damage\|attack\|life\|pillz\|power and damage\|pillz and life\|life and pillz)( per M)? min Y` | enemy, `-X`, borne `Y` |
| 12 | `-X (life\|pillz) min Y` (forme backlash) | ally, `-X`, borne `Y` ; `-X players pillz min Y` → both |
| 13 | tout le reste | non supporté, raison `unknown core: <texte normalisé>` |

Types composés : `power and damage` → `["power", "damage"]`, `pillz and life` / `life and pillz` → `["pillz", "life"]`.

Suffixe `per M` → `how` : `pillz left`→`nb_pillz_left`, `life left`→`nb_life_left`, `life lost`→`nb_life_lost`,
`pillz lost`→`nb_pillz_lost`, `opp damage`→`nb_dam_opp` ; `damage`, `round`, `opp power` → non supporté
(`unsupported multiplier: per <m>`).

Explicitement non supportés (raison dédiée) : `cards …`, `… impose`, `cancel leader`, `consume`, `corrupt`,
`combust`, `corrosion`, `mindwipe`, `rebirth`, `xantiax`, `recover … out of …`, `remove ability conditions`,
et les mots-clés seuls (`beyond`, `bypass`, `hazard`, `illusion`, `infiltrated`, `limitless`, `tie-break`,
`counter-attack`).

### Exemples golden (encodage manuel du template, à reproduire à l'identique)

| Texte | target | types | value | how | borne | conditions |
|---|---|---|---|---|---|---|
| `-2 Opp Power, Min 1` | enemy | [power] | -2 | "" | 1 | [] |
| `Growth: -1 Opp Power, Min 4` | enemy | [power] | -1 | growth | 4 | [] |
| `Courage: Damage +3` | ally | [damage] | 3 | "" | -1 | [courage] |
| `Power +4` | ally | [power] | 4 | "" | -1 | [] |
| `-3 Opp Damage, Min 2` | enemy | [damage] | -3 | "" | 2 | [] |
| `Support: Damage +1` | ally | [damage] | 1 | support | -1 | [] |
| `Equalizer: -1 Opp Pow. & Dam., Min 1` | enemy | [power, damage] | -1 | equalizer | 1 | [] |
| `Stop Opp. Bonus` | enemy | [bonus] | 0 | stop | -1 | [] |
| `Support: Attack +3` | ally | [attack] | 3 | support | -1 | [] |
| `Support: Reanimate: +1 Life` | ally | [reanimate] | 1 | support | -1 | [] |

Le template encode `Stop Opp. Bonus` avec `value: 5`, sans signification pour le moteur : il est ramené à `0`.

## 4. Chargement des cartes

- Nouveau `src/adapters/repositories/card_repository.py` : `get_official_card(name) -> (canonical_name, data)`,
  lecture de `data/jsonData_officiel.json` via `BASE_DIR`, chargée une seule fois (cache module),
  recherche insensible à la casse (comportement actuel conservé) ; `ValueError` si la carte est inconnue.
- `Card.__init__(card_name, nb_stars)` : utilise le repository ; `power`/`damage` convertis en `int`
  (le scraping laisse `"5 "`) ; `ability_description` / `bonus_description` = texte brut (chaînes, plus
  des listes vides) ; `ability` / `bonus` = `parse_capacity(...).capacity` (donc `Capacity` ou `None`) ;
  `ValueError` si le niveau d'étoiles n'existe pas (comportement actuel conservé).
- `Card.from_dict_template` tolère `bonus` / `ability` à `null` ; `Card.to_dict` les sérialise déjà en `null`.
- Suppression de la chaîne morte `Game.from_dict` → `Player.from_dict` → `Card.from_dict` :
  `from_dict_template` est l'unique désérialiseur.
- `create_game` démarre à `nb_turn = 1` (convention fixée au point 2 : numéro du round en cours).

## 5. Garde-fous dans le moteur

`check_capacity_condition` (`process_round.py`) :
- accepte `capacity is None` → retourne `True` (la carte n'a pas de capacité, rien à désactiver) ;
- évalue et consomme les conditions de début de round (`courage`, `revenge`, `confidence`, `reprisal`,
  `symmetry`, `asymmetry`, `bet X`) ; **laisse en place** les conditions différées (`defeat`, `backlash`,
  `victory_defeat`) et retourne `True` s'il ne reste que celles-ci ;
- lève `ValueError` uniquement pour une condition réellement inconnue.

Sémantique conservée pour les conditions connues (mêmes règles ally/enemy qu'aujourd'hui). C'est le bug #7
du rapport ; il devient bloquant dès qu'une vraie carte porte `Defeat:`.

## 6. Rapport de couverture — `scripts/capacity_coverage.py`

Exécutable depuis `UrbanPy/Backend_fastAPI` (`python scripts/capacity_coverage.py`). Parcourt les
descriptions distinctes de `jsonData_officiel.json` (bonus + abilities de tous les niveaux, 906 chaînes),
affiche : nombre supportées / non supportées, pourcentage, puis les non supportées groupées par `reason`
(triées par fréquence décroissante) — c'est la feuille de route du chantier « finir de gérer les pouvoirs ».
Code de sortie 0 toujours (outil de lecture, pas une CI).

## 7. Tests

- `tests/test_capacity_parser.py` :
  - golden : les 10 textes du tableau §3 donnent exactement le dict attendu (`to_dict()` comparé) ;
  - un test par forme de cœur (#2 à #12), par famille de préfixe (condition, multiplicateur, non supporté,
    inconnu), par suffixe `per`, par synonyme d'écriture (`Pow. & Dam.`, `Atk.`, `Dmg`, `Att.`, `Conf.`,
    `Vict. Or Def.`, `- X`, `pow/dam`, `Pillz Opp.`) ;
  - non supportés → `capacity is None`, `supported is False`, `reason` non vide ;
  - texte vide / `No Ability` / `Ability at Level 3` → `None`, supporté ;
  - **couverture** : sur les 906 descriptions distinctes, aucune exception, et
    `nb_supportées >= N` où `N` est la valeur mesurée à l'implémentation (pinnée dans le test, mise à jour
    quand la couverture progresse ; le test échoue si elle régresse).
- `tests/test_card_loading.py` : `Card("Aamir", 3)` (power 5, damage 4, ability Growth structurée,
  bonus All Stars), carte inconnue → `ValueError`, niveau inexistant → `ValueError`,
  `Ability at Level 3` → `ability is None`, capacité non supportée → `ability is None` mais description
  conservée ; aller-retour `to_dict` / `from_dict_template` avec `ability = None`.
- `tests/test_process_round.py` : `check_capacity_condition(None)` → `True` ; `["defeat"]` → `True` et la
  condition reste ; `["courage", "defeat"]` avec courage satisfait → `True` et il reste `["defeat"]` ;
  condition inconnue → `ValueError`.
- `tests/test_api.py` : `POST /init_game/` avec 2 × 4 vraies cartes → 200 et `game_id` ; puis un round
  joué sur cette partie → 200.
- Les suites existantes (42 tests) restent vertes ; le template modifié (`value` de Stop → 0) n'affecte
  ni les fixtures (auto-contenues) ni `test_engine`.

## 8. Fichiers

Nouveaux : `src/core/parsing/__init__.py`, `src/core/parsing/capacity_parser.py`,
`src/adapters/repositories/card_repository.py`, `scripts/capacity_coverage.py`,
`tests/test_capacity_parser.py`, `tests/test_card_loading.py`.
Modifiés : `src/core/domain/card.py`, `player.py`, `game.py`, `src/core/services/game_service.py`,
`src/core/use_cases/process_round.py`, `data/template_game_v1.json`, `tests/test_api.py`,
`tests/test_process_round.py`.
Convention : fichiers existants en CRLF conservés tels quels, nouveaux fichiers en LF.
