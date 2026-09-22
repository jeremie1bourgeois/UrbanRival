# UrbanRival

Réimplémentation du jeu de cartes **Urban Rivals** : un moteur de règles en Python (FastAPI) et une interface web (Vue 3).
Objectif à terme : une IA capable de gagner un maximum de parties (plan détaillé : [docs/IA.md](docs/IA.md)).

## État du projet

| | |
|---|---|
| Cartes jouables | **2 497** (36 clans), données scrapées d'iclintz.com le 2026-09-15, illustrations incluses |
| Pouvoirs (abilities / bonus) | **1 386 / 1 396 descriptions gérées (99,3 %)**, 2 487 cartes sur 2 497 entièrement gérées — `python scripts/capacity_coverage.py` liste le reste |
| Moteur | 4 niveaux d'effets (méta, stats, fin de round, persistants), bonus de clan (Oculus infiltré compris), Leaders (Team, Tie-break, Counter-attack, Limitless), conditions Courage/Revenge/Confidence/Reprisal/Symmetry/Asymmetry/Stop/Killshot/Perfect/Bet/Versus/After/Unison/Disunion/Defeat/Backlash/Victory or Defeat, Tune Out, Impose, Cards, Consume/Combust/Mindwipe/Corrosion, Xantiax, Corrupt, Fatal Killshot ; journal des effets de chaque round |
| Tests | 535 backend (pytest) + 24 front (vitest) ; **corpus combinatoire du moteur** : 113 501 rounds (chaque capacité, chaque interaction méta, chaque condition, effets persistants, Leaders, Oculus, égalités/KO, parties aléatoires) rejoués contre des digests versionnés ; balayage de robustesse sur toutes les descriptions gérées ; 33 combats réels Urban Rivals rejoués à l'identique (`data/ur_battles/`) |
| Interface | composition de deck (recherche, filtre par clan, decks aléatoires, statut des bonus, decks mémorisés), partie de 4 rounds contre un second joueur, historique des rounds, fin de partie, effets persistants |

Non gérés : 9 capacités uniques sans règle publiée (Beyond, Bypass, Hazard, Illusion, Overdose, Perfection, Rebirth,
Remove Ability Conditions, une coquille de Bugamon), soit 9 cartes. Jour/nuit est tiré au sort à la création de la
partie : les cartes à `Day:` / `Night:` et le bonus GhosTown changent de texte.

## Structure

```
UrbanPy/Backend_fastAPI/       backend FastAPI
  main.py                      endpoints : /cards, /init_game/, /init_game/template, /process_round/{id}, /save_for_test
  src/core/domain/             Game, Player, Card, Capacity, PersistentEffect
  src/core/parsing/            capacity_parser.py : texte d'ability -> Capacity (vocabulaire du moteur)
  src/core/use_cases/          process_round.py + apply_capacity_lvl_1..4.py (le moteur) + multipliers.py
  src/core/services/           game_service.py : parties persistées en JSON (data/game/, ignoré par git)
  src/core/engine/             contrat du moteur pur (état compact, cartes compilées), API de référence step / play / legal_actions / terminal,
                               mains aléatoires réalistes, scénarios combinatoires et corpus de non-régression pour un moteur compilé
  src/adapters/repositories/   accès aux données officielles, sauvegarde des parties
  src/adapters/scraping/       extracteur HTML iclintz (pur, testé)
  scripts/                     scraper, rapport de couverture, balayage de robustesse, fixtures d'exemple, corpus du moteur,
                               capture (ur_capture.js) et import (import_ur_battles.py) de combats réels
  data/jsonData_officiel.json  les cartes (seule source de vérité)
  data/template_game_v1.json   partie d'exemple à 8 cartes
  data/engine_digests.json     digests du corpus combinatoire (le corpus lui-même, data/engine_corpus/, se régénère et n'est pas versionné)
  data/test/                   fixtures de rejeu (voir « Tests de régression par fixtures »)
  data/ur_battles/             combats réels capturés dans le client officiel, rejoués par tests/test_ur_battles.py
  tests/
UrbanVue/                      front Vue 3 + TypeScript + Tailwind (Vite)
UrbanPy/script/                pipeline historique d'extraction des patterns de capacités (all_capacities_v*.json)
docs/superpowers/              spec et plan du parseur de capacités
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

Ouvrir http://localhost:5173 : le second joueur joue sur le même écran, composer deux
decks de 4 cartes (recherche, filtre par clan ou « aléatoire »), puis jouer. Le bouton « Sauvegarder le dernier round
pour les tests » enregistre le round dans `data/test/test_N/` (voir ci-dessous).

## Tests

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python -m pytest          # 535 tests (~70 s) ; -m "not corpus" : 507 tests en 4 s
cd UrbanVue && npm test && npm run lint && npm run build           # 24 tests, lint, type-check + build
```

Les tests du moteur sont écrits **de bout en bout** : un texte d'ability (« Growth: -1 Opp Power, Min 4 ») est parsé puis
joué dans un round, et le résultat attendu est calculé à la main d'après les règles.

### Corpus combinatoire du moteur (test différentiel pour un port)

`src/core/engine/scenarios.py` construit, sans hasard, 113 501 rounds en huit familles : **solo** (chacune des 1 358
capacités distinctes, en pouvoir puis en bonus, victoire/défaite × premier/second × rounds 1-4, plus les mains et mises
qui remplissent ses conditions), **interactions** (chaque forme de capacité face aux Stop, Protection, Copy, Cancel,
Exchange, Impose, Tune Out adverses, dans les deux emplacements), **planchers** (tous les couples de réducteurs sur une
même carte, règle « plancher le plus haut d'abord »), **persistants**, **leaders**, **oculus**, **combat** (égalités,
KO, Reanimate, fin de partie, bords des mises) et **aleatoire** (parties complètes). Beaucoup sont enregistrés dans les
deux orientations (camps échangés) : le moteur traite l'allié avant l'ennemi et, avec des planchers, l'ordre compte.

`tests/test_engine_golden.py` rejoue chaque famille et exige le digest versionné dans `data/engine_digests.json` :
**tout changement de règle fait échouer le test**, à régénérer consciemment. `tests/test_engine_properties.py` vérifie
les invariants (déterminisme, bornes, cartes jouées, symétrie miroir sauf asymétries épinglées).

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python scripts/build_engine_corpus.py   # écrit data/engine_corpus/ (~95 Mo) et met à jour les digests
```

Pour comparer un autre moteur (le port Rust) : générer le corpus, puis pour chaque ligne de `<famille>.jsonl` — `deck`
(indice dans `<famille>.decks.json`), `state`, `ally_action`, `enemy_action` (carte, pillz_fight, fury) — calculer l'état
suivant et exiger `next_state` et `outcome` (puissance, dégâts, attaque, vainqueur de chaque carte). Le vocabulaire des
indices (hows, types, conditions, clans, sortes d'effets) est dans `vocabulary.json` ; le format des états dans
`src/core/engine/contract.py`. L'identifiant `id` de chaque ligne nomme la famille, la capacité, la sonde et le contexte.

### Tests de régression par fixtures

Chaque dossier `data/test/test_N/` contient l'état d'une partie avant et après un round. `tests/test_fixtures_replay.py`
rejoue le coup et exige l'état exact. Pour en ajouter : jouer un round dans l'interface, vérifier qu'il est juste,
cliquer « Sauvegarder … pour les tests », commiter le dossier créé. `scripts/regenerate_example_fixtures.py` régénère les
trois fixtures d'exemple quand le format de partie change.

### Combats réels (oracle)

`data/ur_battles/*.json` sont des combats joués dans le client officiel d'Urban Rivals et capturés avec
`scripts/ur_capture.js`. `tests/test_ur_battles.py` rejoue chaque round avec les mêmes choix et exige les valeurs
officielles (puissance, dégâts, attaque, vainqueur, vies, pillz) : c'est l'oracle qui tranche les règles incertaines.
Procédure de capture et d'import : [docs/ORACLE.md](docs/ORACLE.md).

## Scripts utiles

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python scripts/capacity_coverage.py       # descriptions non gérées par le parseur, groupées par raison
.venv/bin/python scripts/engine_crash_sweep.py      # joue un round avec chaque description gérée, liste les exceptions
.venv/bin/python scripts/scrape_official_cards.py   # re-scrape iclintz.com (cache dans data/.scrape_cache, reprise possible)
```

## Règles du moteur

Un round : conditions de début de round → niveau 1 (Stop / Protection / Copy / Cancel / Exchange, résolus simultanément)
→ niveau 2 (Power / Damage / Attack) → attaques (puissance × pillz, fury +2 dégâts pour 3 pillz ; sous Tune Out,
puissance 1 et attaque = pillz misées) → Killshot → combat
(égalité : moins d'étoiles gagne, puis le joueur qui joue en premier) → KO et Reanimate → niveau 3 (Life / Pillz de fin
de round) → niveau 4 (Poison / Toxin / Heal / Regen / Dope / Repair, qui agissent à la fin des rounds suivants).

Le bonus de clan n'est actif qu'avec au moins deux cartes du clan en main ; l'ability « Team: » d'un Leader s'applique à
chaque carte jouée s'il est le seul Leader en main.

Les décisions de règles prises sans source, leur vérification contre le glossaire officiel et les points encore
ouverts sont consignés dans [docs/REGLES.md](docs/REGLES.md) ; les combats réels (`docs/ORACLE.md`) les tranchent.

## Feuille de route

État des lieux détaillé, décisions de règles et travail restant : [docs/ROADMAP.md](docs/ROADMAP.md).

1. Règles : trancher les points encore ouverts de `docs/REGLES.md` § 5 (cycles de Stops, Leader et son Team,
   Mindwipe / Combust, Limitless…) par des combats réels capturés selon `docs/ORACLE.md`
2. Backend : moteur compilé rapide derrière le contrat `src/core/engine/` (~1 ms par round aujourd'hui, ~10 µs visés
   pour le solveur), persistance en mémoire/SQLite, mise à jour FastAPI/Pydantic
3. IA : équilibre de Nash par round, solveur exact de référence, fonction de valeur apprise sur ses résultats,
   arène d'évaluation, intégration dans l'interface — étapes détaillées dans [docs/IA.md](docs/IA.md)
