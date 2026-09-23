# UrbanRival — feuille de route

Ce document liste **ce qui reste à faire**. L'état actuel (cartes, moteur, tests, interface) est dans le
[README](../README.md#état-du-projet) ; les décisions de règles et le registre des questions ouvertes sont dans
[`REGLES.md`](REGLES.md) ; le plan IA détaillé dans [`IA.md`](IA.md). Façon de travailler (branches, commits, TDD) :
`CLAUDE.md`.

## Ordre recommandé

1. **Règles** : trancher les six points du registre `REGLES.md` § « Registre des règles non tranchées » (R1-R6) par
   des combats réels capturés selon [`ORACLE.md`](ORACLE.md).
2. **Backend** : moteur compilé rapide derrière le contrat `src/core/engine/` (~1 ms par round aujourd'hui, ~10 µs
   visés), persistance en mémoire/SQLite.
3. **IA** : suite du plan détaillé dans [`IA.md`](IA.md).

## Moteur et règles

- Les six points du registre `REGLES.md` § « Registre des règles non tranchées » (R1 ordre entre camps, R2 per
  damage en défaite, R3 per life/pillz lost au-dessus du départ, R4 Protection contre « Cards », R5 Exchange contre
  Copie/Impose, R6 Perfection sans règle publiée).
- **Ce que le moteur ne modélise pas du tout**, hors round : le tirage de la main (deck de 8 → 4 cartes au hasard),
  les contraintes de composition (plafond d'étoiles, cartes interdites par mode), les scores de tournoi / ELO /
  Deathmatch, la progression Survivor, les modificateurs Coliseum et les chronomètres. Un mode se réduit dans le
  moteur à sa **situation de départ** (vies et pillz par camp, premier joueur), réglable depuis `/init_game/` et le
  deck builder.
- Avant de figer un port du moteur (Rust ou autre), trancher R1-R4 en priorité : ce sont des ordres de résolution et
  des bornes qui changeraient le format même de l'état ou du corpus de non-régression.

## Backend

| Tâche | Détail |
|---|---|
| **Port compilé (Rust)** | Le contrat pur (`src/core/engine/contract.py`, API `step` / `legal_actions` / `terminal`) et le corpus combinatoire (113 501 rounds, `scripts/build_engine_corpus.py`, digests dans `data/engine_digests.json`) sont l'oracle de comparaison. Pour vérifier un autre moteur : générer le corpus, puis pour chaque ligne de `<famille>.jsonl` — `deck` (indice dans `<famille>.decks.json`), `state`, `ally_action`, `enemy_action` — calculer l'état suivant et exiger `next_state` et `outcome` identiques. Vocabulaire des indices : `vocabulary.json` ; format des états : `contract.py`. |
| **Persistance** | Fichiers JSON par round (`data/game/`) → stockage mémoire + SQLite optionnel ; `get_new_game_id` est relatif au dossier courant (le serveur doit être lancé depuis `UrbanPy/Backend_fastAPI`). |
| **Dette technique** | `requirements.txt` fige `fastapi==0.100.0` (2023) et des validateurs Pydantic v1 (`@validator`, dépréciés → `field_validator`) ; CORS à rendre configurable ; `print` de debug et `debug=True` dans `main.py` ; le front dépend du CDN d'Urban Rivals pour les images (option : script de téléchargement local). |

## Front

- Tests de composants (aucun aujourd'hui : seuls la logique pure et le modèle sont testés) ; éventuellement des
  tests de bout en bout (Playwright).
- Montrer au second joueur la carte jouée par le premier avant la résolution (règle UR : la carte est visible, pas
  les pillz) — aujourd'hui rien n'est révélé avant la résolution.
- Réintégrer un sélecteur d'adversaire IA (retiré du front avec `POST /ai_pick/` le temps que la partie se joue à
  deux sur le même écran) quand l'IA sera prête à jouer.

## IA

Plan, décisions et mesures détaillés : [`IA.md`](IA.md). Travail en cours sur la branche `feat/ia-tous-modes`
(étapes 1 à 3 bis du plan : Nash à un round, solveur exact, mesures de coût) — à fusionner sur accord explicite.
Suite : étape 4 (exploitation, modèle d'adversaire, évaluation de decks, intégration dans l'interface).

## Divers

- Branches distantes déjà fusionnées dans `main` : à supprimer (`git branch -r --merged main`).
- `.claude/launch.json` (ignoré par git) lance backend et front depuis le dossier du projet avec `.venv` ; à
  recréer si besoin.
- `UrbanPy/script/` (pipeline historique `all_capacities_v*.json`) n'est plus référencé par le code ; à archiver ou
  supprimer.
- Le scraper peut être relancé quand le site publie de nouvelles cartes (`scripts/scrape_official_cards.py`) ; les
  compteurs pinnés dans `tests/test_api.py` et `tests/test_capacity_parser.py` sont alors à mettre à jour.
