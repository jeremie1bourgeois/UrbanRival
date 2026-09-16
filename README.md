# UrbanRival

Réimplémentation du jeu de cartes **Urban Rivals** : un moteur de règles en Python (FastAPI) et une interface web (Vue 3).
Objectif à terme : une IA par apprentissage par renforcement.

## État du projet

| | |
|---|---|
| Cartes jouables | **2 497** (36 clans), données scrapées d'iclintz.com le 2026-09-15, illustrations incluses |
| Pouvoirs (abilities / bonus) | **1 116 / 1 310 descriptions gérées (85 %)** — `python scripts/capacity_coverage.py` liste le reste |
| Moteur | 4 niveaux d'effets (méta, stats, fin de round, persistants), bonus de clan, Leaders, conditions Courage/Revenge/Confidence/Reprisal/Symmetry/Asymmetry/Stop/Killshot/Bet/Versus/Defeat/Backlash/Victory or Defeat |
| Tests | 309 backend (pytest) + 15 front (vitest) ; balayage de robustesse sur toutes les descriptions gérées |
| Interface | composition de deck (recherche parmi toutes les cartes), partie de 4 rounds, fin de partie, effets persistants |

Non gérés pour l'instant (par nombre de descriptions) : Unison (62), After (37), Cards (15), Recover (11), Mindwipe (7), Disunion (7), Perfect (7), Combust (6), Impose (5) et quelques mécaniques à 1-3 cartes. `Day:` est considéré toujours valide, `Night:` jamais.

## Structure

```
UrbanPy/Backend_fastAPI/       backend FastAPI
  main.py                      endpoints : /cards, /init_game/, /init_game/template, /process_round/{id}, /save_for_test
  src/core/domain/             Game, Player, Card, Capacity, PersistentEffect
  src/core/parsing/            capacity_parser.py : texte d'ability -> Capacity (vocabulaire du moteur)
  src/core/use_cases/          process_round.py + apply_capacity_lvl_1..4.py (le moteur) + multipliers.py
  src/core/services/           game_service.py : parties persistées en JSON (data/game/, ignoré par git)
  src/adapters/repositories/   accès aux données officielles, sauvegarde des parties
  src/adapters/scraping/       extracteur HTML iclintz (pur, testé)
  scripts/                     scraper, rapport de couverture, balayage de robustesse, fixtures d'exemple
  data/jsonData_officiel.json  les cartes (seule source de vérité)
  data/template_game_v1.json   partie d'exemple à 8 cartes
  data/test/                   fixtures de rejeu (voir « Tests de régression par fixtures »)
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

Ouvrir http://localhost:5173 : composer deux decks de 4 cartes (ou « Partie d'exemple »), puis jouer. Le bouton
« Sauvegarder le dernier round pour les tests » enregistre le round dans `data/test/test_N/` (voir ci-dessous).

## Tests

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python -m pytest          # 309 tests
cd UrbanVue && npm test && npm run lint && npm run build           # 15 tests, lint, type-check + build
```

Les tests du moteur sont écrits **de bout en bout** : un texte d'ability (« Growth: -1 Opp Power, Min 4 ») est parsé puis
joué dans un round, et le résultat attendu est calculé à la main d'après les règles.

### Tests de régression par fixtures

Chaque dossier `data/test/test_N/` contient l'état d'une partie avant et après un round. `tests/test_fixtures_replay.py`
rejoue le coup et exige l'état exact. Pour en ajouter : jouer un round dans l'interface, vérifier qu'il est juste,
cliquer « Sauvegarder … pour les tests », commiter le dossier créé. `scripts/regenerate_example_fixtures.py` régénère les
trois fixtures d'exemple quand le format de partie change.

## Scripts utiles

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python scripts/capacity_coverage.py       # descriptions non gérées par le parseur, groupées par raison
.venv/bin/python scripts/engine_crash_sweep.py      # joue un round avec chaque description gérée, liste les exceptions
.venv/bin/python scripts/scrape_official_cards.py   # re-scrape iclintz.com (cache dans data/.scrape_cache, reprise possible)
```

## Règles du moteur

Un round : conditions de début de round → niveau 1 (Stop / Protection / Copy / Cancel / Exchange, résolus simultanément)
→ niveau 2 (Power / Damage / Attack) → attaques (puissance × pillz, fury +2 dégâts pour 3 pillz) → Killshot → combat
(égalité : moins d'étoiles gagne, puis le joueur qui joue en premier) → KO et Reanimate → niveau 3 (Life / Pillz de fin
de round) → niveau 4 (Poison / Toxin / Heal / Regen / Dope / Repair, qui agissent à la fin des rounds suivants).

Le bonus de clan n'est actif qu'avec au moins deux cartes du clan en main ; l'ability « Team: » d'un Leader s'applique à
chaque carte jouée s'il est le seul Leader en main.

Deux règles ont été tranchées sans certitude et sont isolées dans le code avec un test : « Stop Opp. Ability » contre
« Stop Opp. Bonus » (les deux s'appliquent) et « Cancel Opp. Life Modif. » (ne touche pas au poison).

## Feuille de route

1. Mécaniques restantes : Unison, After, Cards, Recover… (règles à documenter d'abord)
2. Front : ModalCard (pillz / fury) à moderniser, historique des rounds, mode contre l'ordinateur
3. IA : exposer un `step(state, action)` pur (le moteur l'est déjà, il manque l'emballage) puis apprentissage par renforcement
