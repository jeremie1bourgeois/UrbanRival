# Une IA imbattable en ELO : plan de travail

Document de chantier, ouvert le 2026-09-16, revu le 2026-09-17 (déroulé du jeu confirmé par l'utilisateur,
plan simplifié en conséquence). Le but : **que personne ne puisse battre l'IA**, en **parties ELO**. Tout est
organisé autour de ce but, pas autour de « trouver un bon coup ». État d'avancement en tête de chaque étape.

## Contexte

Le moteur de règles est mûr (1 386/1 396 descriptions gérées, oracle de combats réels).
Le socle prévu en ROADMAP § D1 est en place : `src/core/ai/engine.py` (API pure
`step` / `legal_actions` / `result` / `reward`, sans persistance), `evaluation.py`, deux adversaires
qui simulent un coup d'avance (`greedy`, `minimax`), `arena.py` + `scripts/ai_arena.py`,
`scripts/bench_engine.py`. Mesures : un round 0,17 ms, une copie d'état 0,035 ms, ~1 500 parties/s,
une décision de recherche ~66 ms.

## Ce que « imbattable » veut dire, et comment on le mesure

Urban Rivals est un jeu à somme nulle où, dans un round, la mise en pillz de l'adversaire est cachée.
Dans un jeu de cette forme :

- **Aucune règle de mise déterministe n'est imbattable.** Miser selon une règle fixe se contre, comme au
  pierre-feuille-ciseaux : un adversaire qui observe finit par gagner. L'IA doit **tirer sa mise au sort
  selon des probabilités calculées** (stratégie mixte). C'est vrai aussi du `minimax` écrit aujourd'hui.
  (Le choix de carte, lui, n'a pas à être mixte : voir « Un round se résout par carte ».)
- **Il existe une stratégie que personne ne peut battre** : l'équilibre de Nash. Elle garantit un
  score espéré ≥ **la valeur du duel** face à **n'importe quel** adversaire, aussi fort soit-il, y compris
  un adversaire qui connaîtrait notre code.
- La mesure de ce but, ce n'est pas un taux de victoire contre l'heuristique : c'est
  **l'exploitabilité ε** = ce qu'un adversaire parfait gagnerait contre nous au-delà de la valeur du duel.
  ε → 0 signifie « personne ne peut faire mieux contre nous que ce que les mains permettent ». C'est
  l'indicateur que tout le plan poursuit.
- Contre un adversaire *imparfait* (tout joueur humain, l'IA du site), on veut en plus le **punir** :
  c'est la couche d'exploitation (étape 6), qui transforme « jamais battu » en « gagne presque tout ».

Deux limites à assumer, et à dire franchement :

- **La valeur dépend des mains.** Nash garantit « pas pire que la valeur du duel », et cette valeur est
  négative quand notre main est plus faible : contre un adversaire parfait mieux servi, on perd en moyenne —
  le moins possible, mais on perd. Par affrontement, la promesse est donc « joue chaque duel de façon
  optimale » ; seul le deck (phase 2) déplace la valeur. Ne pas s'étonner du premier match perdu contre
  une meilleure main.
- À mains égales et premier joueur tiré au sort, même une IA parfaite ne gagne pas 100 % des parties : si
  l'adversaire joue aussi parfaitement, le résultat est équilibré et les nulles existent.

« Imbattable » = **personne ne prend l'avantage sur la durée à deck égal**, et toute erreur adverse se paie.

## Cadre : le mode ELO

Déroulé d'une partie, confirmé par l'utilisateur le 2026-09-17 et par le combat capturé
(`data/ur_battles/1181426.json`, `rule_id: 3`) :

1. Chaque joueur : **14 vies**, **12 pillz**, **4 cartes visibles des deux côtés** (tirées des 8 du deck).
2. Round 1 : un joueur tiré au sort pose une carte + une mise (0 à 12) + éventuellement la fury (3 pillz de
   plus). Le second voit **la carte seulement** — ni la mise ni la fury — et répond par une carte + une mise
   (+ fury). Résolution du combat.
3. Le second du round précédent pose en premier au suivant (alternance p1, p0, p1, p0). 4 rounds, ou KO avant.

Deux propriétés de ce déroulé portent tout le plan :

- **Entre deux rounds, tout est public.** Après résolution, l'attaque de chaque carte (donc la mise), la fury,
  les vies et les pillz restantes sont visibles. Aucune croyance ne se transporte d'un round au suivant :
  l'état `(round, vies, pillz, cartes restantes, effets persistants, premier joueur)` décrit tout, et
  l'induction arrière sur cet état est **exacte** — pas de belief state, pas de CFR.
- **La seule information cachée est la mise, à l'intérieur d'un round.** Le choix de carte du premier joueur
  est vu avant la réponse : c'est la mise, et elle seule, qui doit être tirée au sort.

À reprendre en phase 2 (composition de deck) : liste des cartes bannies en ELO, limite d'étoiles, statut des
Leaders. Sans effet sur la façon de jouer une main donnée (confirmé par l'utilisateur).

## Architecture visée

```
état public (round, vies, pillz, cartes restantes, effets, premier joueur)
        │
        ├── equilibrium.py    Nash d'un jeu matriciel à somme nulle (LP scipy) — rien d'autre n'est nécessaire
        ├── solver.py         induction arrière mémoïsée : rounds 4 et 3 exacts
        ├── round_matrix.py   matrice de gains d'un round (chemin analytique rapide + repli moteur)
        ├── policy.py         nash_pick : résout le sous-jeu, tire la mise au sort dans la stratégie mixte
        └── exploit.py        modèle d'adversaire + meilleure réponse *sûre*
```

### Un round se résout par carte : pas de forme séquentielle

Le second joueur voit la carte et répond **par carte révélée, indépendamment**. Si le premier joue la carte `c`
avec probabilité `p(c)` et sa mise selon `σ_c`, sa valeur est `Σ_c p(c) · min_y σ_cᵀ M_c y`, où `M_c` est la
matrice (mises du premier sur `c`) × (carte et mise du second) dont chaque cellule vaut `V(état suivant)`.
Le second minimise chaque terme séparément ; le premier maximise en mettant tout le poids sur la carte de
meilleure valeur `v_c* = max_σ min_y σᵀ M_c y`. Donc :

- **En premier : la carte est pure** (celle de meilleure valeur ; à égalité, n'importe quel mélange des
  ex æquo), **seules les pillz sont mixtes**. Prévisible sans dommage : l'adversaire voit la carte de toute
  façon.
- **En second : la réponse à la carte vue est la stratégie colonne optimale de `M_c`** — y compris pour une
  carte que l'équilibre ne jouerait pas.
- **`equilibrium.py` n'a besoin que du LP d'un jeu matriciel.** Un état se résout par au plus 4 LP de taille
  ≤ 23 × 92, dont on garde le max. Pas de forme séquentielle.

### Pourquoi c'est calculable

Par carte, 23 actions au plus (13 mises + 10 avec fury). Round 4 : une carte chacun, **un LP ≤ 23 × 23**,
quelques millisecondes. Round 3 : deux cartes chacun, **2 LP ≤ 23 × 46**, 2 116 feuilles de round 4.
Round 2 : 3 LP ≤ 23 × 69, 4 761 feuilles ; round 1 : 4 LP ≤ 23 × 92, **8 464 feuilles**, chacune un sous-jeu
entier. Le LP n'est jamais le goulot : c'est la valeur des feuilles. D'où, pour les rounds 1-2 : abstraction
des mises et évaluation approchée des feuilles (étape 4). C'est la recette AlphaZero adaptée aux coups
simultanés — la recherche fait la force, l'évaluation de feuille ne fait qu'estimer.

## Étapes

### Étape 0 — Socle et étalons — ✅ fait le 2026-09-16

API moteur pure (D1), évaluation d'état, adversaires `greedy` et `minimax` (un coup d'avance simulé),
banc d'essai et mesure de débit. Ces adversaires restent les étalons contre lesquels se mesurent les
progrès — ils ne sont pas l'IA visée : ils sont déterministes, donc exploitables.

Réglage mesuré : `evaluation.PILLZ_WEIGHT` à 1 faisait brader les pillz dès le round 1 (glouton à
12 % contre l'heuristique) ; à 4, glouton 84 % et minimax 83 % contre l'aléatoire (60 parties).
Le modèle de réponses adverses compte autant que les poids : tirer les réponses uniformément parmi
les coups légaux revient à supposer un adversaire qui mise n'importe comment.
*Réserve* : 60 parties, c'est ±13 points à 95 %. Ces chiffres ordonnent grossièrement (12 % contre 84 %),
ils ne départagent pas 62 % de 73 % — à remesurer avec la méthode de l'étape 5.

### Étape 1 — Modéliser exactement le jeu ELO — ✅ fait le 2026-09-17

Règle d'information **confirmée par l'utilisateur** : quels que soient la partie et le mode, le second
joueur voit toujours la carte posée par le premier, jamais ses pillz ni sa fury. C'est donc la règle du moteur.

- `engine.elo_game(mains, rng)` : 14 vies, 12 pillz, **premier joueur tiré au sort** puis alterné
  (`new_game(..., ally_first=...)`, `first_side`, `plays_first`). L'arène joue des parties ELO.
- `engine.play_out` respecte l'ordre et l'information : le premier joue en aveugle, le second reçoit
  `revealed_card`. Toutes les stratégies ont la signature `(game, side, rng, revealed_card=None)` ;
  les recherches s'en servent pour n'envisager que les mises de l'adversaire **sur cette carte**.
- `/ai_pick` accepte `revealed_card_index` et **refuse** qu'on le donne au joueur qui pose en premier
  (ce serait tricher). Front : la carte posée est entourée et nommée (« en face : X (pillz cachées) »),
  et l'ordinateur ne la reçoit que lorsqu'il joue en second.
- Mesure du gain : la même stratégie, privée de l'information quand elle joue en second, perd —
  glouton 55 %, minimax 60,5 % pour la version informée (100 parties). *Réserve* : ±10 points ; 55 % n'est
  pas distinguable du hasard, 60,5 % à peine. Le gain attendu est modeste par nature (l'information ne sert
  que sur les rounds joués en second, et une recherche à un coup n'en tire qu'une partie), mais il reste
  **à établir** sur 1 000 parties avec intervalle. C'est le solveur qui l'exploitera pleinement.

Non nécessaire pour jouer : la **liste des bannis ELO** ne change rien à l'IA (l'utilisateur l'a
confirmé) — elle ne concerne que la composition de deck, donc la phase 2.

### Étape 2 — Solveur exact de fin de partie, sur le moteur actuel (3-5 j)

Le solveur d'abord, la vitesse ensuite. Avec `engine.step` à 0,17 ms, un round 4 se résout en
23 × 23 × 0,17 ms ≈ **90 ms** — jouable dans l'interface dès maintenant — et un round 3 en dizaines de
secondes (2 116 feuilles, quelques centaines d'états de round 4 distincts après mémoïsation) : lent, mais
testable. Ce chemin lent est l'oracle de l'étape 3, et il existe avant qu'on optimise quoi que ce soit.

- `equilibrium.py` : `solve_matrix(M) -> (valeur, stratégie ligne, stratégie colonne)` par programmation
  linéaire (`scipy.optimize.linprog`, HiGHS). Élimination itérée des mises dominées avant le LP (l'attaque est
  monotone en pillz : miser plus que nécessaire est dominé). Tests : pile ou face → 50/50, équilibre pur
  connu, jeu symétrique → valeur 0, matrice à lignes dominées.
- `solver.py` : induction arrière mémoïsée sur une clé canonique (round, vies, pillz, cartes restantes,
  effets persistants, premier joueur). Par état : une matrice par carte du premier joueur, un LP chacune, max
  sur les cartes. Round 4, puis round 3.
- Livrables : une stratégie `solver` **parfaite sur les deux derniers rounds** — donc déjà imbattable
  en fin de partie — exposée dans `STRATEGIES` et `/ai_pick` (jalon visible : le dernier round ne se perd
  plus), et un **oracle de valeurs** pour tester le reste.
- Point d'attention : `linprog` coûte 1 à 5 ms de frais fixes par appel. Si les dizaines de milliers de
  petits LP de l'étape 4 le rendent trop lent, un solveur dédié aux petites matrices (ou un lot vectorisé)
  le remplace — sans changer l'interface de `solve_matrix`.

### Étape 3 — Matrice de round rapide (2-3 j, guidée par le profil)

L'étape 4 demande des millions de cellules : 0,17 ms l'unité est 100 à 1 000 fois trop lent. On optimise
là où le profil de l'étape 2 le montre, le chemin lent restant l'oracle.

- `round_matrix.py` : pour un couple de cartes, calculer **en une passe** puissances et dégâts après
  pouvoirs (indépendants des pillz dans l'immense majorité des cas), puis dériver toute la matrice
  (p₁ × p₂) analytiquement — `attaque = puissance × pillz`, comparaison, dégâts, effets de fin de round.
  Vectorisé numpy.
- **Repli obligatoire** vers le moteur, cellule par cellule, dès qu'une capacité en jeu dépend des
  pillz : `Bet >/< N`, `per Pillz Left`, `Recover`, `Tune Out`, et les conditions `Killshot` / `Perfect`
  (qui dépendent du rapport des attaques).
- **Test qui autorise le raccourci** : balayage façon `scripts/engine_crash_sweep.py` sur toutes les
  descriptions gérées — matrice rapide identique, cellule à cellule, à `engine.step`.
- Cible : round 3 exact en ~0,1 s.

### Étape 4 — Recherche à profondeur limitée (1-2 semaines)

- **Abstraction des mises** : grille (0, 1, 2, 3, 4, 6, 8, tout + variantes fury) au lieu de 0..12,
  affinée autour du coup retenu ; le round 2 tombe de ~4 700 à ~1 000 feuilles, le round 1 de ~8 500 à
  ~2 000.
- **Évaluation des feuilles : résoudre grossièrement plutôt qu'apprendre.** Une feuille de round 3 s'évalue
  par une résolution exacte à grille grossière (0, part, part + 2, tout, fury) : 2 cartes × 5 mises de chaque
  côté, 100 feuilles de round 4 en LP 5 × 5 — bien sous la milliseconde avec l'étape 3. Même recette pour une
  feuille de round 2 (grille grossière sur deux rounds). Ça passe par le moteur, donc ça comprend toutes les
  capacités sans avoir à généraliser, et ça s'affine en resserrant la grille. Nash est **sensible aux erreurs
  de gains** — une évaluation à ±0,05 déplace le support de la stratégie mixte — c'est pourquoi une valeur
  exacte-mais-grossière est préférée à une régression.
- **Plan B, pour la latence seulement : V̂(état) apprise.** Régression sur les valeurs exactes du solveur
  (rounds 3-4), puis amorçage pour les rounds 1-2. Traits : round, premier joueur, vies, pillz, et par carte
  étoiles / puissance / dégâts / bonus actif, plus les `Capacity` structurées par le parseur ; modèle linéaire
  de référence, puis gradient boosting ou petit MLP. Ne se justifie que si la grille grossière ne tient pas le
  budget au round 1 — budget qui est un choix d'interface, pas une contrainte du site.
- `policy.nash_pick` : construit le sous-jeu, le résout, **joue la carte pure et tire la mise au sort dans
  la stratégie mixte** (graine pour la reproductibilité) ; en second, répond à la carte révélée.
- Budget : < 1 s par décision dans l'interface, réglable (profondeur, finesse des deux grilles).

### Étape 5 — Prouver l'invincibilité (en parallèle des étapes 2-4)

- **Mesurer avec un intervalle, d'abord.** 60 parties → ±13 points, 100 → ±10 : les écarts mesurés jusqu'ici
  sont dans le bruit. `arena.MatchResult` affiche un intervalle de Wilson à 95 % ; les duels tournent sur
  ≥ 1 000 parties (0,5 s par partie avec recherche : 8 minutes) ; chaque paire de mains est rejouée côtés
  échangés (variance réduite). Aucune conclusion n'entre dans ce document sans intervalle.
- **`scripts/exploitability.py`** : meilleure réponse à notre politique, **l'adversaire dans l'espace
  d'actions complet** (0..12 + fury), notre politique restant abstraite. Une ε calculée dans le jeu abstrait
  n'est pas une exploitabilité (pathologie classique des abstractions). Rounds 3-4 : ε = 0 par construction.
  Rounds 1-2 : une **estimation**, à présenter comme telle, dont on publie la courbe à chaque version.
- Échelle ELO interne (`scripts/ai_arena.py`) : aléatoire, heuristique, glouton, minimax, solveur de fin
  de partie, politique Nash, **version précédente** (garde-fou anti-régression).
- **Fidélité des règles** : un solveur exploite les bugs du moteur autant que les erreurs adverses.
  Chaque combat ELO importé (`docs/ORACLE.md`, `tests/test_ur_battles.py`) est une vérification de plus ;
  viser d'abord les capacités du pool ELO et les points non tranchés (cycles de Stops, Team du Leader,
  Tune Out + fury, Mindwipe/Combust). Les 10 descriptions non gérées restent hors des mains jouées.

### Étape 6 — Punir les adversaires réels (après le Nash ; à sacrifier si le temps manque)

- `exploit.py` : un **modèle de population**, pas d'adversaire — 4 observations par partie ne permettent pas
  de modéliser un joueur. On modélise comment les joueurs du site misent en général (selon le round, le
  budget, la carte vue), à partir des combats capturés (collecte passive, donc mince) et des parties jouées
  dans l'interface.
- **Meilleure réponse sûre** : jouer la meilleure réponse au modèle en bornant la perte par rapport à
  la valeur de Nash (*restricted Nash response*) — on exploite sans redevenir exploitable si le modèle
  se trompe. C'est ce qui fait passer de « jamais battu » à « gagne presque à chaque fois ».

### Phase 2 — composer le deck (hors périmètre aujourd'hui, préparé par ce plan)

Le solveur donne la **valeur d'équilibre d'un affrontement de mains**. Évaluer un deck de 8 cartes,
c'est moyenner cette valeur sur les tirages 4 parmi 8 des deux camps, face au méta ELO. Rien à
réarchitecturer : il suffira de brancher un optimiseur (recherche locale sous contrainte d'étoiles et
de bans) sur `solver.value(main_a, main_b)`.

### Ce qui n'est pas retenu, et pourquoi

- Le self-play PPO/DQN « nu » de la ROADMAP § E : dans un jeu à coups simultanés, il converge vers une
  politique déterministe **exploitable** — l'inverse du but. Les variantes qui convergent vraiment
  (NFSP, PSRO, R-NaD/DeepNash) restent en réserve si la taille du jeu résiste, mais ici le jeu est petit :
  **résoudre est plus simple et plus fort qu'apprendre**. Gymnasium reste un emballage utile pour
  expérimenter, pas le cœur.
- La **forme séquentielle** (Koller–Megiddo–von Stengel) : correcte, mais inutile ici — le second joueur
  répond carte par carte, un round se résout en jeux matriciels indépendants (voir Architecture).
- **V̂ apprise comme évaluation première des feuilles** : reléguée en plan B (étape 4), la résolution à
  grille grossière comprenant les capacités sans généraliser.

## Vérification

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python -m pytest -q                      # 450 tests aujourd'hui
.venv/bin/python scripts/engine_crash_sweep.py     # 0 exception
.venv/bin/python scripts/capacity_coverage.py | head -1
.venv/bin/python scripts/bench_engine.py           # débit moteur, coût d'une décision
.venv/bin/python scripts/ai_arena.py --games 1000  # échelle entre stratégies, avec intervalles
.venv/bin/python scripts/exploitability.py         # (étape 5) LE critère : ε → 0
```

Tests à écrire, dans l'esprit du dépôt (attentes calculées à la main) :

- `equilibrium` : jeux matriciels de référence (pile ou face → 50/50, équilibre pur, symétrie → 0), lignes
  et colonnes dominées éliminées sans changer la valeur.
- `solver` : sur des fins de partie minuscules, valeur trouvée = valeur calculée à la main (ex. dernier
  round, 1 vie contre 2, 3 pillz contre 0) ; **en premier, la carte jouée est pure et seules les mises sont
  mixtes ; en second, la réponse dépend de la carte vue** ; la politique optimale bat toute stratégie fixe
  dans ce sous-jeu.
- `round_matrix` : identité cellule à cellule avec `engine.step` sur toutes les capacités gérées (chemin
  lent de l'étape 2 = chemin rapide de l'étape 3, même valeur de solveur).
- `policy` : distribution sur des coups légaux, reproductible à graine fixée, strictement mixte là où
  elle doit l'être.
- `arena` : intervalle de Wilson juste sur des cas connus (0/10, 5/10, 1 000 parties).
- Bout en bout : une partie ELO complète dans l'interface contre l'adversaire « nash » avant de déclarer
  le chantier fini (convention du dépôt).

## Risques et points à confirmer

1. ~~**La règle d'information**~~ → confirmée le 2026-09-17 : le second joueur voit toujours la carte,
   jamais les pillz ni la fury ; **et tout est public entre les rounds**. Conséquences : induction arrière
   exacte, un round = jeux matriciels par carte, pas de forme séquentielle.
2. ~~**Le pool ELO**~~ → sans effet sur le jeu de l'IA ; à reprendre en phase 2 (composition de deck).
3. **Le chemin analytique de l'étape 3** : c'est lui qui rend l'étape 4 possible. S'il ne tient pas
   pour trop de capacités, il faudra un moteur de round dédié (numpy, sans objets) — plus de travail,
   même résultat. L'étape 2 ne dépend pas de lui.
4. **Les règles encore incertaines** : le solveur amplifie les erreurs du moteur ; l'oracle doit grossir
   au même rythme que l'IA.
5. **Temps de calcul dans l'interface** : finesse des deux grilles (mises du sous-jeu, mises de l'évaluation
   de feuille) et profondeur sont les boutons à tourner ; V̂ est le dernier recours.
6. **ε n'est exacte que sur les rounds 3-4.** Sur les rounds 1-2 c'est une estimation, bornée par la qualité
   de l'évaluation des feuilles ; le doc et les courbes doivent le dire.
