# UrbanRival — état des lieux et travail restant

Document de passation, à jour au 2026-09-16 (`main` = `d4e1afc`). Le README décrit comment lancer et tester ;
ce document décrit **où on en est et ce qui reste**, pour reprendre le travail dans une nouvelle session.

## 1. Où on en est

| Domaine | État |
|---|---|
| Données | 2 497 cartes, 36 clans, illustrations (URLs CDN), scrapées d'iclintz.com le 2026-09-15 par `scripts/scrape_official_cards.py` (cache disque, reprise possible, `--from-cache` pour regénérer sans réseau) ; les icônes de clan de « Versus », « After » et des abilities d'Oculus sont rendues en texte |
| Parseur de capacités | 1 386 / 1 396 descriptions gérées (99,3 %) ; `scripts/capacity_coverage.py` liste les 10 restantes (capacités uniques sans règle publiée) |
| Cartes entièrement gérées | toutes sauf les porteuses des 9 descriptions restantes (Genesis, Robert Cobb, Bugamon, Memento, Kate, Glibon Cr, Hekate, Administrator, Nemo Cr) |
| Moteur | 4 niveaux réécrits et testés (méta, stats, fin de round, persistants) ; bonus de clan (≥ 2 du clan, Oculus infiltré sur ses clans listés, Leaders), conditions Courage / Revenge / Confidence / Reprisal / Symmetry / Asymmetry / Stop / Killshot / Perfect / Bet / Versus / After / Unison / Disunion / Defeat / Backlash / Victory or Defeat / Team ; Tune Out, Impose, Cards, Consume / Combust / Mindwipe / Corrosion, Xantiax, Corrupt, Fatal Killshot, Sinister Symmetry, Leaders Tie-break / Counter-attack / Limitless / Per Round ; `scripts/engine_crash_sweep.py` : 0 exception |
| API | `/cards`, `/init_game/`, `/init_game/template`, `/process_round/{id}`, `/save_for_test` |
| Front | deck builder (recherche, filtre clan, aléatoire, statut des bonus, decks mémorisés), partie à deux, historique des rounds, fin de partie, effets persistants, illustrations |
| Tests | 429 backend (pytest) + 24 front (vitest) ; CI GitHub Actions (backend + front) ; 3 fixtures de rejeu `data/test/` + 1 combat réel `data/ur_battles/` |
| Dépôt | nettoyé (IDE, binaires, doublons), fins de ligne LF (`.gitattributes`), README |

### Décisions de règles prises sans certitude (à confirmer contre les règles officielles)

Chacune est isolée dans une fonction et couverte par un test : changer d'avis = une ligne + un test.

**Audit du 2026-09-16 : voir `docs/REGLES.md`** — les six règles contredites par les sources (Stops, Bet, Infiltrated,
Cancel Life Modif., Reanimate, Versus) ont été **corrigées** le même jour ; le tableau ci-dessous reflète l'état corrigé.

| Règle retenue | Où |
|---|---|
| Stops résolus **en chaîne** (un Stop stoppé ne stoppe rien) — règle officielle, art. 91 du support | `apply_capacity_lvl_1._stopped_slots`, tests `test_official_example_1/2_*` |
| Cycles (SoA contre SoA, Protection: Ability + Protection: Bonus face à SoA + SoB) : les Stops gagnent — confirmé par l'utilisateur (2026-09-21) | idem, `test_soa_versus_soa_is_a_cycle_where_both_stops_win`, `test_double_protection_versus_all_stop_is_a_cycle_where_the_stops_win` |
| « Cancel Opp. Life Modif. » **suspend pour le round** les effets persistants adverses (poison/toxin/heal/regen ; Pillz : dope/consume), qui reprennent au round suivant — glossaire officiel 56 | `Card.cancelled_modifs`, `apply_capacity_lvl_4._suspended` |
| Reanimate = « Defeat: +X Life » qui marche aussi depuis 0 (règle officielle) ; les effets de fin de round sont sautés sur KO | `apply_capacity_lvl_3.apply_reanimate` + boucle de niveau 3, `process_round` |
| Recover X out of Y : ⌊pillz posées × X / Y⌋, **minimum 1** (glossaire 53), fury et **pillz gratuite comprises** — combat réel 1347075 (2026-09-21) | `apply_capacity_lvl_3.recovered_pillz`, `data/ur_battles/1347075.json` |
| Sur une même carte, la réduction au **plancher le plus haut s'applique d'abord** (modificateurs de niveau 2) — combats réels 1347131 et 1294992, seule règle conforme aux deux (REGLES 3.6 bis) | `apply_capacity_lvl_2._slots_highest_floor_first`, `data/ur_battles/1347131.json`, `1294992.json` |
| Infiltrated (Oculus) — règle officielle : un seul autre clan → celui-là ; deux → celui de la **carte seule** ; trois ou deux Oculus → rien. Chaque Leader est son propre clan : un Leader seul est la carte seule (l'Oculus le rejoint et le Cancel Leader l'annule), deux Leaders + une carte = trois clans (rien) — combats réels 1346878, 1347500, 1347671, 1347602 (2026-09-21) ; la liste des clans imprimée sur la carte ne restreint que le bonus adopté et l'ability | `clan.infiltrated_clan`, `multipliers._support`, `data/ur_battles/1346878.json`, `1347671.json` |
| Team (Leader) : s'applique à chaque carte jouée, Leader compris, seulement si Leader unique (deux exemplaires du même Leader s'annulent) — confirmé par l'utilisateur (2026-09-21) | `process_round.leader_team_capacity`, `tests/test_leader_team.py` |
| Versus (clans) : s'active si la **main** adverse contient une carte du clan, pas seulement la carte en face — règle officielle | `process_round.check_capacity_condition` |
| Bet > N / < N : compare `pillz_fight` (**pillz gratuite comprise**, fury exclue) — règle officielle | `process_round._bet_condition_met` |
| Killshot : attaque > 0 et ≥ 2 × attaque adverse, évaluée après les modificateurs d'attaque | `process_round.apply_killshot_condition` |
| per damage : dégâts réellement infligés (0 en défaite) | `multipliers._nb_damage_inflicted` |
| Copy : copie le **texte** adverse (bonus seulement s'il est actif), ses conditions sont **réévaluées pour le copieur** — combat 1349481 ; Copy vs Copy → rien | `apply_capacity_lvl_1.apply_copies`, `process_round.drop_unmet_conditions` |
| Fury : +2 dégâts ajoutés **après** les modificateurs de dégâts (utilisateur ; glossaire 56 : « Annul Modif Dégâts n'annule pas la Fury ») | `process_round` |
| Toxine / Régén / Dope / Repair / Consume / Combust (Mindwipe) agissent **dès le round joué** (glossaire 51, 52 ; Repair, Combust : utilisateur) ; Poison / Heal aux rounds suivants | `apply_capacity_lvl_4.IMMEDIATE_KINDS` |
| « Per Pillz Left » : pillz **avant la mise**, pillz gratuite exclue (glossaire 66) | `multipliers._nb_pillz_left` |
| Jour/nuit tiré au sort en début de partie ; de nuit les cartes prennent `night_ability` / `night_bonus` (REGLES 3.13) | `game_service.create_game`, `Card(night=)` |

### Ce que le moteur ne modélise pas du tout
- Le tirage de la main : les decks sont composés carte par carte (pas de collection, pas de tirage 8 → 4).
- Le premier joueur d'une partie est toujours l'allié (`turn = True` dans `create_game`) ; dans le jeu il est tiré au sort (utilisateur, 2026-09-21), comme jour/nuit.
- Les pouvoirs ci-dessous (§ 2.A).

## 2. Travail restant

### A. Pouvoirs non gérés

Tout ce qui a une règle publiée est codé (voir `docs/REGLES.md` § 4). Reste, sans règle trouvée ni sur le site ni sur le
wiki : **Beyond** (Genesis, 5e round — hors périmètre), **Perfection** (Glibon Cr), `Growth: -1 Power And Damage, Min 4`
(Bugamon, coquille probable).

**Exclus définitivement du moteur et de l'IA** (décision utilisateur, 2026-09-21) : **Hazard** (Administrator),
**Illusion** (Kate), **Bypass** (Robert Cobb), **Overdose** (Hekate), **Remove Ability Conditions** (Memento),
**Rebirth 1, Max. 1** (Nemo Cr), **Counter-attack** (Ashigaru — le code existant reste, mais la règle n'est plus à
vérifier ni à traiter par l'IA ; le premier joueur du combat 1349159 contredisait la règle énoncée), **Limitless**
(Fractal — même statut : code conservé, règle plus à vérifier). Leurs définitions sont conservées dans `docs/REGLES.md` § 4 pour mémoire ; ne pas les
compter parmi les pouvoirs restant à gérer.

Tranché par combat réel (1294992, 2026-09-20) : un Cancel Opp. X Modif. adverse annule le X Exchange, les deux cartes
gardent leurs valeurs imprimées (REGLES § 7).
Confirmé par l'utilisateur (2026-09-21) : Tune Out ramène la puissance des deux cartes à 1 et compare les pillz **sans la fury** (combat 1248952) ; Mindwipe = Combust ; Repair,
Combust et Mindwipe agissent dès le round joué (si la carte gagne) ; Perfect = écart d'attaque < puissance ; Brawl
compte les exemplaires comme Support ; Cancel Opp. Life Modif. saute le tic immédiat d'une Toxine.

### B. Fiabilité des règles existantes
1. ~~Confirmer les décisions du tableau § 1 contre les règles officielles~~ → fait (`docs/REGLES.md`) ; appliquer les corrections listées en § 3 de ce document.
2. **Oracle = combats réels** (fait le 2026-09-16, premier combat reproduit à l'identique) : jouer un combat dans le
   client web d'Urban Rivals avec `scripts/ur_capture.js` chargé, importer `urRecords()` avec `scripts/import_ur_battles.py` (procédure complète : `docs/ORACLE.md`),
   `tests/test_ur_battles.py` rejoue chaque round et exige les valeurs officielles (puissance, dégâts, attaque,
   vainqueur, vies, pillz). Viser les points non tranchés (plancher de Recover, Exchange contre Copie/Impose)
   et les clans à bonus méta. Le modèle `abilityData` du
   client (`docs/ur-abilitydata-modele.md`) s'accumule passivement avec les combats (pas de scraping API : piste abandonnée).
3. Le journal des effets (D2, fait) rend ces vérifications immédiates : comparer le journal au déroulé réel.

### C. Front — reste mineur
- Tests de composants (aucun : seuls la logique pure et le modèle sont testés) ; éventuellement des tests de bout en bout (Playwright).
- ~~Historique : afficher les effets appliqués~~ → fait (D2).
- Montrer au second joueur la carte jouée par le premier (règle UR : la carte est visible, pas les pillz) — aujourd'hui rien n'est révélé avant la résolution.
- Tirer un premier joueur aléatoire / laisser choisir.

### D. Backend — préparer l'IA (recommandé en premier)
| # | Tâche | Détail |
|---|---|---|
| D1 | **API moteur pure** | `Engine.step(state, action) → (state, result)` et `legal_actions(state)`. `process_round` est pur ; extraire la persistance de `game_service`. Figer une représentation d'état (`Game.to_dict`) et d'action (carte, pillz, fury). |
| D2 | ~~**Journal des effets**~~ | **Fait le 2026-09-16** : `src/core/domain/journal.py` (`Journal`, `note`, `recording`), `Round.log` (entrées `{side, card, source, text}`), renvoyé par `/process_round`, déplié dans l'historique du front. Les fixtures de rejeu comparent l'état sans le journal. |
| D3 | Performance | Mesuré le 2026-09-18 : ~1 ms par round (deepcopy + `process_round`). Le solveur exact et la génération d'exemples (`docs/IA.md` § 5.3-5.4) demandent ~10 µs par round : état compact, sans deepcopy ni re-parsing des capacités, code compilé. |
| D4 | Persistance | Fichiers JSON par round (`data/game/`) → stockage mémoire + SQLite optionnel ; `get_new_game_id` est relatif au dossier courant (le serveur doit être lancé depuis `UrbanPy/Backend_fastAPI`). |
| D5 | Dette | `requirements.txt` (FastAPI 0.100 de 2023, `@validator` Pydantic v1 déprécié → `field_validator`), CORS configurable, `print` de debug dans `main.py`, `debug=True`. Le front dépend du CDN d'Urban Rivals pour les images (option : script de téléchargement local). |

### E. IA
Plan détaillé, décisions et mesures : **`docs/IA.md`** (2026-09-18). En résumé : (0) API moteur pure, générateur de
mains, arène d'évaluation, joueurs étalons ; (1) équilibre de Nash du round en cours par programme linéaire ;
(2) solveur exact par induction à rebours, référence de mesure ; (3) fonction de valeur apprise sur les résultats du
solveur, recherche + réseau ; (4) modèle d'adversaire, évaluation de decks, intégration dans l'interface.
L'apprentissage par renforcement par essais-erreurs (Gymnasium, PPO/DQN) envisagé ici auparavant est abandonné.

### F. Divers
- Branches distantes déjà fusionnées à supprimer : `chore/infra`, `feat/donnees-scraping`, `feat/front-c`, `feat/pouvoirs-vortex-oculus`, `fix/bugs-moteur-et-fixtures`, `gameStruct`.
- `.claude/launch.json` (ignoré par git) lance backend et front depuis le dossier du projet avec `.venv` ; à recréer si besoin.
- `UrbanPy/script/` (pipeline historique `all_capacities_v*.json`) n'est plus utilisé par le code ; à archiver ou supprimer.
- Le scraper peut être relancé quand le site publie de nouvelles cartes ; les compteurs pinnés dans `tests/test_api.py` (2 497) et `tests/test_capacity_parser.py` (1 396, plancher 1 386) sont alors à mettre à jour.

## 3. Conventions de travail utilisées jusqu'ici
- Une branche par chantier (`feat/…`, `fix/…`, `chore/…`), commits en français, fusion `--no-ff` dans `main` après accord de l'utilisateur, push après chaque chantier.
- TDD : test rouge avant tout code ; tests du moteur écrits de bout en bout (texte d'ability → parseur → round joué) avec des attentes calculées à la main ; balayage + couverture relancés après chaque changement de moteur ; plancher de couverture pinné dans les tests.
- Vérification dans le navigateur (deck → partie) avant de déclarer un chantier front terminé.
- Ordre recommandé pour la suite : **B2 (combats réels) → D1 → E**, en traitant les pouvoirs de A au fil des règles retrouvées.
