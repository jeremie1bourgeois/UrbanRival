# UrbanRival

Réimplémentation du jeu de cartes **Urban Rivals** : un moteur de règles en Python (FastAPI) et une interface web
(Vue 3). Objectif à terme : une IA capable de gagner un maximum de parties (plan détaillé :
[docs/IA.md](docs/IA.md)).

## État du projet

| | |
|---|---|
| Cartes jouables | **2 497** (36 clans), données scrapées d'iclintz.com le 2026-09-15, illustrations incluses |
| Pouvoirs (abilities / bonus) | **1 386 / 1 395 descriptions gérées (99,4 %)** — `python scripts/capacity_coverage.py` liste le reste ; les 9 non gérées sont documentées dans [docs/REGLES.md](docs/REGLES.md#pouvoirs-exclus-du-moteur-et-de-lia) |
| Moteur | 4 niveaux d'effets (méta, stats, fin de round, persistants), bonus de clan (Oculus infiltré compris), Leaders (Team, Tie-break, Counter-attack, Limitless), une vingtaine de conditions numériques et de position, jour/nuit, journal des effets de chaque round — décisions de règles : [docs/REGLES.md](docs/REGLES.md) |
| Tests | 569 backend (pytest, dont 113 501 rounds de corpus combinatoire) + 28 front (vitest) ; 56 combats réels Urban Rivals rejoués à l'identique — détail : § Tests ci-dessous |
| Interface | composition de deck (recherche, filtre par clan, decks aléatoires, decks mémorisés), choix du mode (Classic, ELO, duel, vies/pillz/premier joueur personnalisés), partie de 4 rounds à deux sur le même écran, historique, fin de partie, effets persistants |

Feuille de route (ce qui reste à faire) : [docs/ROADMAP.md](docs/ROADMAP.md).

## Structure

```
UrbanPy/Backend_fastAPI/       backend FastAPI
  main.py                      endpoints : /cards, /init_game/ (mains + situation de départ), /init_game/template, /process_round/{id}, /save_for_test
  src/core/domain/              Game, Player, Card, Capacity, PersistentEffect
  src/core/parsing/             capacity_parser.py : texte d'ability -> Capacity (vocabulaire du moteur)
  src/core/use_cases/           process_round.py + apply_capacity_lvl_1..4.py (le moteur) + multipliers.py
  src/core/services/            game_service.py : parties persistées en JSON (data/game/, ignoré par git)
  src/core/engine/              contrat du moteur pur (état compact, cartes compilées), API step / play / legal_actions / terminal,
                                 mains aléatoires réalistes, scénarios combinatoires et corpus de non-régression pour un moteur compilé
  src/adapters/repositories/    accès aux données officielles, sauvegarde des parties
  src/adapters/scraping/        extracteur HTML iclintz (pur, testé)
  scripts/                      scraper, rapport de couverture, balayage de robustesse, corpus du moteur,
                                 capture (ur_capture.js) et import (import_ur_battles.py) de combats réels, recherche dans la collection possédée
  data/jsonData_officiel.json   les cartes (seule source de vérité)
  data/collection/               collection du compte Urban Rivals « jere'm », relevée passivement (voir docs/ORACLE.md)
  data/engine_digests.json      digests du corpus combinatoire (le corpus lui-même, data/engine_corpus/, se régénère et n'est pas versionné)
  data/test/                    fixtures de rejeu (voir « Tests » ci-dessous)
  data/ur_battles/               combats réels capturés dans le client officiel, rejoués par tests/test_ur_battles.py
  tests/
UrbanVue/                      front Vue 3 + TypeScript + Tailwind (Vite)
UrbanPy/script/                 pipeline historique d'extraction des patterns de capacités (all_capacities_v*.json), plus utilisé
```

## Lancer le jeu

Backend (Python 3.12) :

```bash
cd UrbanPy/Backend_fastAPI
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Front (Node 22) :

```bash
cd UrbanVue
npm ci
npm run dev
```

Ouvrir http://localhost:5173 : les deux joueurs jouent sur le même écran, composer deux decks de 4 cartes
(recherche, filtre par clan ou « aléatoire »), puis jouer. Le bouton « Sauvegarder le dernier round pour les tests »
enregistre le round dans `data/test/test_N/` (voir ci-dessous).

## Tests

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python -m pytest          # 569 tests (~75 s) ; -m "not corpus" : 541 tests en ~4 s
cd UrbanVue && npm test && npm run lint && npm run build           # 28 tests, lint, type-check + build
```

Les tests du moteur sont écrits **de bout en bout** : un texte d'ability (« Growth: -1 Opp Power, Min 4 ») est parsé
puis joué dans un round, et le résultat attendu est calculé à la main d'après les règles. Trois familles s'y
ajoutent :

- **Corpus combinatoire** (`tests/test_engine_golden.py`, `test_engine_properties.py`) : 113 501 rounds sans hasard
  couvrant chaque capacité, chaque interaction méta, chaque plancher, les effets persistants, les Leaders, l'Oculus
  et des parties aléatoires, rejoués contre des digests versionnés (`data/engine_digests.json`) — tout changement de
  règle fait échouer le test, à régénérer consciemment avec `python scripts/build_engine_corpus.py`. C'est aussi le
  test différentiel prévu pour un port du moteur (détail : [docs/ROADMAP.md](docs/ROADMAP.md)).
- **Fixtures de rejeu** (`data/test/test_N/`, `tests/test_fixtures_replay.py`) : état d'une partie avant/après un
  round, rejoué et comparé à l'exact. Pour en ajouter : jouer un round dans l'interface, cliquer « Sauvegarder …
  pour les tests », commiter le dossier créé. `scripts/regenerate_example_fixtures.py` régénère les fixtures
  d'exemple quand le format de partie change.
- **Combats réels** (`data/ur_battles/*.json`, `tests/test_ur_battles.py`) : 56 combats joués dans le client
  officiel et rejoués à l'identique (puissance, dégâts, attaque, vainqueur, vies, pillz) — l'oracle qui tranche les
  règles incertaines. Procédure de capture : [docs/ORACLE.md](docs/ORACLE.md).

## Scripts utiles

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python scripts/capacity_coverage.py       # descriptions non gérées par le parseur, groupées par raison
.venv/bin/python scripts/engine_crash_sweep.py      # joue un round avec chaque description gérée, liste les exceptions
.venv/bin/python scripts/scrape_official_cards.py   # re-scrape iclintz.com (cache dans data/.scrape_cache, reprise possible)
```

## Règles du moteur

Un round : conditions de début de round → niveau 1 (Stop / Protection / Copy / Cancel / Exchange, résolus
simultanément) → niveau 2 (Power / Damage / Attack) → attaques (puissance × pillz, fury +2 dégâts pour 3 pillz) →
Killshot → combat (égalité : moins d'étoiles gagne, puis le premier joueur) → KO et Reanimate → niveau 3 (Life /
Pillz de fin de round) → niveau 4 (Poison / Toxin / Heal / Regen / Dope / Repair, aux rounds suivants).

Décisions de règles, sources et registre des points encore ouverts : [docs/REGLES.md](docs/REGLES.md). Les combats
réels ([docs/ORACLE.md](docs/ORACLE.md)) les tranchent.

## Documentation

- [docs/ROADMAP.md](docs/ROADMAP.md) — ce qui reste à faire
- [docs/REGLES.md](docs/REGLES.md) — décisions de règles, sources, registre des questions ouvertes
- [docs/REGLES-glossaire-officiel.md](docs/REGLES-glossaire-officiel.md) — texte intégral du glossaire officiel
- [docs/IA.md](docs/IA.md) — plan de construction de l'IA
- [docs/ORACLE.md](docs/ORACLE.md) — capturer des combats réels comme tests
- [docs/ur-abilitydata-modele.md](docs/ur-abilitydata-modele.md) — modèle de règles observé côté client officiel
