# UrbanRival — état des lieux et travail restant

Document de passation, à jour au 2026-09-16 (`main` = `d4e1afc`). Le README décrit comment lancer et tester ;
ce document décrit **où on en est et ce qui reste**, pour reprendre le travail dans une nouvelle session.

## 1. Où on en est

| Domaine | État |
|---|---|
| Données | 2 497 cartes, 36 clans, illustrations (URLs CDN), scrapées d'iclintz.com le 2026-09-15 par `scripts/scrape_official_cards.py` (cache disque, reprise possible) |
| Parseur de capacités | 1 132 / 1 310 descriptions gérées (86 %) ; `scripts/capacity_coverage.py` liste le reste par raison |
| Cartes entièrement gérées | 2 340 / 2 497 (94 %) — les 157 restantes ont au moins un pouvoir non géré à leur niveau max |
| Moteur | 4 niveaux réécrits et testés (méta, stats, fin de round, persistants) ; bonus de clan (≥ 2 du clan, Oculus infiltré, Leaders), conditions Courage / Revenge / Confidence / Reprisal / Symmetry / Asymmetry / Stop / Killshot / Bet / Versus / Defeat / Backlash / Victory or Defeat / Team ; `scripts/engine_crash_sweep.py` : 0 exception sur toutes les descriptions gérées |
| API | `/cards`, `/init_game/`, `/init_game/template`, `/process_round/{id}`, `/ai_pick/{id}`, `/save_for_test` |
| Front | deck builder (recherche, filtre clan, aléatoire, statut des bonus, decks mémorisés), partie à deux ou contre l'ordinateur (aléatoire / heuristique), historique des rounds, fin de partie, effets persistants, illustrations |
| Tests | 332 backend (pytest) + 22 front (vitest) ; CI GitHub Actions (backend + front) ; 3 fixtures de rejeu `data/test/` |
| Dépôt | nettoyé (IDE, binaires, doublons), fins de ligne LF (`.gitattributes`), README |

### Décisions de règles prises sans certitude (à confirmer contre les règles officielles)

Chacune est isolée dans une fonction et couverte par un test : changer d'avis = une ligne + un test.

| Règle retenue | Où |
|---|---|
| Stop Opp. Ability contre Stop Opp. Bonus : **les deux s'appliquent** (résolution simultanée) | `apply_capacity_lvl_1._stopped_kinds`, test `test_stops_resolve_simultaneously_soa_versus_sob` |
| Protection cyclique (Protection: Ability + Protection: Bonus face à SoA + SoB) : les Stops gagnent | idem |
| « Cancel Opp. Life Modif. » **n'annule pas** le poison | `apply_capacity_lvl_1._strip_types` |
| Reanimate : uniquement pour le joueur tombé à 0, via la carte qu'il vient de jouer ; les effets de fin de round sont sautés sur KO | `apply_capacity_lvl_3.apply_reanimate`, `process_round` |
| Recover X out of Y : ⌊pillz misées × X / Y⌋, **fury comprise** | `apply_capacity_lvl_3.recovered_pillz` |
| Infiltrated (Oculus) : bonus du clan **majoritaire** des autres cartes (hors Oculus/Leader), l'Oculus compte comme membre, égalité → rien | `process_round.infiltrated_clan` |
| Team (Leader) : s'applique à chaque carte jouée, Leader compris, seulement si Leader unique | `process_round.leader_team_capacity` |
| Bet > N / < N : compare les pillz **misées** (pillz_fight − 1, sans la fury) | `process_round._bet_condition_met` |
| Killshot : attaque > 0 et ≥ 2 × attaque adverse, évaluée après les modificateurs d'attaque | `process_round.apply_killshot_condition` |
| per damage : dégâts réellement infligés (0 en défaite) | `multipliers._nb_damage_inflicted` |
| Copy : copie l'emplacement adverse tel que joué (conditions déjà évaluées) ; Copy vs Copy → rien | `apply_capacity_lvl_1._apply_copies` |
| Fury : +2 dégâts ajoutés **après** les modificateurs de dégâts | `process_round` |
| `Day:` toujours valide, `Night:` jamais (décision utilisateur, cycle jour/nuit non modélisé) | `capacity_parser._IGNORED_PREFIXES` |

### Ce que le moteur ne modélise pas du tout
- Le tirage de la main : les decks sont composés carte par carte (pas de collection, pas de tirage 8 → 4).
- Le premier joueur d'une partie est toujours l'allié (`turn = True` dans `create_game`).
- Les pouvoirs ci-dessous (§ 2.A).

## 2. Travail restant

### A. Pouvoirs non gérés — 157 cartes

Règles inconnues de l'utilisateur comme de l'assistant : **à documenter d'abord** (page « Règles » d'Urban Rivals ou wiki
des joueurs), puis chacune se code comme Killshot ou Bet (une condition dans `check_capacity_condition` /
`DEFERRED_CONDITIONS`, ou un multiplicateur dans `multipliers.py`) avec 3-4 tests de bout en bout.

| Mécanique | Cartes (niveau max) | Descriptions | Note |
|---|---|---|---|
| Tune Out (bonus **Cosmohnuts**) | 35 | 1 | tout le clan ; texte « Tune Out » seul |
| Unison: X | 30 | 62 | préfixe de condition, dispersé sur tous les clans |
| After: X (bonus **Tolvack** + abilities) | 30 | 37 | tout le clan Tolvack |
| Cards … (`-2 Cards Damage`, `Cards Damage +2`, `Protection: Cards …`) | 15 | 15 | effet sur toutes les cartes de la main → nouveau type d'effet |
| Impose (`Damage Impose`, `Power Impose`) | 10 | 5 | échange forcé de stat ? |
| Perfect: X | 8 | 7 | condition |
| Consume X, Min Y | 7 | 4 | effet persistant ? |
| Combust X, Min Y / Mindwipe X, Min Y / Xantiax | 13 | 16 | effets persistants ou de fin de round à définir |
| Disunion: X | ~6 | 7 | condition (opposé d'Unison ?) |
| per round, Rebirth, Corrosion, Corrupt, mots-clés seuls (Beyond, Bypass, Hazard, Illusion, Limitless, Tie-break, Counter-attack, Fatal Killshot, Sinister Symmetry, Overdose, Perfection, Remove Ability Conditions) | ~12 | ~15 | rendement faible |
| `unknown core` | — | 6 | `Growth: -1 Power And Damage, Min 4` (coquille du site ?), `Team: Cancel Players X Mod.` (×4), `+1 Attack / Life Lost`-like déjà traités — vérifier avec `capacity_coverage.py` |

Utilisateur : Unison et After sont **volontairement ignorés** tant que leurs règles ne sont pas connues.

### B. Fiabilité des règles existantes
1. Confirmer les décisions du tableau § 1 contre les règles officielles.
2. Alimenter `data/test/` : jouer des rounds dans l'interface, vérifier à la main, « Sauvegarder … pour les tests », commiter.
   Viser en priorité les clans à bonus méta (Nightmare, Skeelz, Piranas, Roots, GHEIST, Raptors, Oblivion, Oculus, Vortex, Montana).
3. Le journal des effets (D2) rendra ces vérifications beaucoup plus rapides.

### C. Front — reste mineur
- Tests de composants (aucun : seuls la logique pure et le modèle sont testés) ; éventuellement des tests de bout en bout (Playwright).
- Historique : afficher les effets appliqués (dépend de D2).
- Montrer au second joueur la carte jouée par le premier (règle UR : la carte est visible, pas les pillz) — aujourd'hui rien n'est révélé avant la résolution.
- Tirer un premier joueur aléatoire / laisser choisir.

### D. Backend — préparer l'IA (recommandé en premier)
| # | Tâche | Détail |
|---|---|---|
| D1 | **API moteur pure** | `Engine.step(state, action) → (state, result)` et `legal_actions(state)` (déjà écrit pour l'IA : `src/core/ai/opponent.legal_picks`). `process_round` est pur ; extraire la persistance de `game_service`. Figer une représentation d'état (`Game.to_dict`) et d'action (`Pick`). |
| D2 | **Journal des effets** | Chaque niveau consigne ce qu'il applique (« Amelia : Power +4 → 7 », « Bhudd : Stop Opp. Bonus stoppe le bonus d'Amelia »). Renvoyer le journal dans `/process_round` et le stocker dans `Round`. Sert au front (historique détaillé), au débogage des règles et aux tests. |
| D3 | Performance | Mesurer `process_round` (deepcopy des capacités, sérialisation) ; le RL a besoin de milliers de parties/s. |
| D4 | Persistance | Fichiers JSON par round (`data/game/`) → stockage mémoire + SQLite optionnel ; `get_new_game_id` est relatif au dossier courant (le serveur doit être lancé depuis `UrbanPy/Backend_fastAPI`). |
| D5 | Dette | `requirements.txt` (FastAPI 0.100 de 2023, `@validator` Pydantic v1 déprécié → `field_validator`), CORS configurable, `print` de debug dans `main.py`, `debug=True`. Le front dépend du CDN d'Urban Rivals pour les images (option : script de téléchargement local). |

### E. IA
1. Adversaires étalons : aléatoire et heuristique existent (`src/core/ai/opponent.py`) ; ajouter un glouton et un minimax à 1 coup.
2. Environnement Gymnasium `UrbanRivalEnv` sur D1 : observation = état sérialisé, action = (carte, pillz, fury), masque des actions illégales (`legal_picks`).
3. Self-play (PPO/DQN — Stable-Baselines3 ou CleanRL), d'abord contre l'aléatoire puis contre lui-même ; decks variés.
4. Évaluation : taux de victoire contre chaque étalon, ELO interne.
5. Intégration : l'agent devient une stratégie de `/ai_pick`.

### F. Divers
- Branches distantes déjà fusionnées à supprimer : `chore/infra`, `feat/donnees-scraping`, `feat/front-c`, `feat/pouvoirs-vortex-oculus`, `fix/bugs-moteur-et-fixtures`, `gameStruct`.
- `.claude/launch.json` (ignoré par git) lance backend et front depuis le dossier du projet avec `.venv` ; à recréer si besoin.
- `UrbanPy/script/` (pipeline historique `all_capacities_v*.json`) n'est plus utilisé par le code ; à archiver ou supprimer.
- Le scraper peut être relancé quand le site publie de nouvelles cartes ; les compteurs pinnés dans `tests/test_api.py` (2 497) et `tests/test_capacity_parser.py` (1 310, plancher 1 132) sont alors à mettre à jour.

## 3. Conventions de travail utilisées jusqu'ici
- Une branche par chantier (`feat/…`, `fix/…`, `chore/…`), commits en français, fusion `--no-ff` dans `main` après accord de l'utilisateur, push après chaque chantier.
- TDD : test rouge avant tout code ; tests du moteur écrits de bout en bout (texte d'ability → parseur → round joué) avec des attentes calculées à la main ; balayage + couverture relancés après chaque changement de moteur ; plancher de couverture pinné dans les tests.
- Vérification dans le navigateur (deck → partie) avant de déclarer un chantier front terminé.
- Ordre recommandé pour la suite : **D1 + D2 → B2 → E**, en traitant les pouvoirs de A au fil des règles retrouvées.
