# Une IA imbattable en ELO : plan de travail

Document de chantier, ouvert le 2026-09-16. Le but : **que personne ne puisse battre l'IA**, en
**parties ELO**. Tout est organisé autour de ce but, pas autour de « trouver un bon coup ».
État d'avancement en tête de chaque étape.

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

- **Aucune stratégie déterministe n'est imbattable.** Miser selon une règle fixe se contre, comme au
  pierre-feuille-ciseaux : un adversaire qui observe finit par gagner. L'IA doit **tirer ses coups au
  sort selon des probabilités calculées** (stratégie mixte). C'est vrai aussi du `minimax` écrit aujourd'hui.
- **Il existe une stratégie que personne ne peut battre** : l'équilibre de Nash. Elle garantit un
  score espéré ≥ 0 face à **n'importe quel** adversaire, aussi fort soit-il, y compris un adversaire
  qui connaîtrait notre code.
- La mesure de ce but, ce n'est pas un taux de victoire contre l'heuristique : c'est
  **l'exploitabilité ε** = ce qu'un adversaire parfait gagnerait contre nous. ε → 0 signifie
  littéralement « personne ne peut le battre ». C'est l'indicateur que tout le plan poursuit.
- Contre un adversaire *imparfait* (tout joueur humain, l'IA du site), on veut en plus le **punir** :
  c'est la couche d'exploitation (étape 6), qui transforme « jamais battu » en « gagne presque tout ».

Une seule limite à assumer : à mains égales et premier joueur tiré au sort, même une IA parfaite ne
gagne pas 100 % des parties — si l'adversaire joue aussi parfaitement, le résultat est équilibré et
les nulles existent. « Imbattable » = **personne ne prend l'avantage sur la durée**, et toute erreur
adverse se paie.

## Cadre : le mode ELO

Confirmé par le combat réel déjà capturé (`data/ur_battles/1181426.json`, `rule_id: 3`) :
**14 vies**, 12 pillz, 4 rounds, **premier joueur tiré au sort au round 1 puis alterné** (p1, p0, p1, p0).

À établir au début du chantier (règles du site + ta connaissance du format) :
liste des cartes **bannies** en ELO, limite d'étoiles du deck, statut des Leaders et de la fury.
Intérêt direct : le pool ELO est bien plus petit que les 2 497 cartes — il définit **les capacités à
fiabiliser en priorité** et les mains sur lesquelles l'IA s'entraîne et se mesure.

Le deck ELO est de 8 cartes dont 4 sont tirées à chaque combat. Pendant le combat, les deux mains sont
publiques : le tirage ne concerne donc que la **phase 2 (composition de deck)**, prévue plus bas.

## Architecture visée

```
état public (round, vies, pillz, cartes restantes, effets, premier joueur)
        │
        ├── round_matrix.py   matrice de gains d'un round (chemin analytique rapide + repli moteur)
        ├── equilibrium.py    Nash d'un jeu matriciel / en forme séquentielle (LP scipy)
        ├── solver.py         induction arrière mémoïsée : rounds 4 et 3 exacts
        ├── value_net.py      V̂(état) apprise, évalue les feuilles des rounds 1-2
        ├── policy.py         nash_pick : résout le sous-jeu, tire au sort dans la stratégie mixte
        └── exploit.py        modèle d'adversaire + meilleure réponse *sûre*
```

Pourquoi c'est calculable : au round 4 il ne reste **une carte par joueur**, la décision se réduit aux
pillz → matrice ~23 × 23, résolue exactement en quelques millisecondes. Au round 3 (2 cartes chacun,
~46 actions), la carte du premier joueur étant visible, la forme séquentielle tient en ~140 variables.
Les rounds 1-2 explosent (~14 000 feuilles valant chacune un sous-jeu) : abstraction des mises +
valeur apprise. C'est la recette AlphaZero adaptée aux coups simultanés — la recherche fait la force,
le réseau ne sert qu'à évaluer les feuilles.

## Étapes

### Étape 0 — Socle et étalons — ✅ fait le 2026-09-16

API moteur pure (D1), évaluation d'état, adversaires `greedy` et `minimax` (un coup d'avance simulé),
banc d'essai et mesure de débit. Ces adversaires restent les étalons contre lesquels se mesurent les
progrès — ils ne sont pas l'IA visée : ils sont déterministes, donc exploitables.

Réglage mesuré : `evaluation.PILLZ_WEIGHT` à 1 faisait brader les pillz dès le round 1 (glouton à
12 % contre l'heuristique) ; à 4, glouton 84 % et minimax 83 % contre l'aléatoire (60 parties).
Le modèle de réponses adverses compte autant que les poids : tirer les réponses uniformément parmi
les coups légaux revient à supposer un adversaire qui mise n'importe comment.

### Étape 1 — Modéliser exactement le jeu ELO — ✅ fait le 2026-09-17

Règle d'information **confirmée par l'utilisateur** : quels que soient la partie et le mode, le second
joueur voit toujours la carte posée par le premier, jamais ses pillz. C'est donc la règle du moteur.

- `engine.elo_game(mains, rng)` : 14 vies, 12 pillz, **premier joueur tiré au sort** puis alterné
  (`new_game(..., ally_first=...)`, `first_side`, `plays_first`). L'arène joue des parties ELO.
- `engine.play_out` respecte l'ordre et l'information : le premier joue en aveugle, le second reçoit
  `revealed_card`. Toutes les stratégies ont la signature `(game, side, rng, revealed_card=None)` ;
  les recherches s'en servent pour n'envisager que les mises de l'adversaire **sur cette carte**.
- `/ai_pick` accepte `revealed_card_index` et **refuse** qu'on le donne au joueur qui pose en premier
  (ce serait tricher). Front : la carte posée est entourée et nommée (« en face : X (pillz cachées) »),
  et l'ordinateur ne la reçoit que lorsqu'il joue en second.
- Mesure du gain : la même stratégie, privée de l'information quand elle joue en second, perd —
  glouton 55 %, minimax 60,5 % pour la version informée (100 parties). Le gain est réel mais modeste :
  l'information ne sert que sur les rounds où l'on joue second, et une recherche à un coup n'en tire
  qu'une partie de la valeur. C'est le solveur qui l'exploitera pleinement.

Non nécessaire pour jouer : la **liste des bannis ELO** ne change rien à l'IA (l'utilisateur l'a
confirmé) — elle ne concerne que la composition de deck, donc la phase 2.

### Étape 2 — Matrice de round rapide (2-3 j)

Le solveur a besoin de millions de résolutions de round : 0,17 ms l'unité est 100 à 1 000 fois trop lent.

- `round_matrix.py` : pour un couple de cartes, calculer **en une passe** puissances et dégâts après
  pouvoirs (indépendants des pillz dans l'immense majorité des cas), puis dériver toute la matrice
  (p₁ × p₂) analytiquement — `attaque = puissance × pillz`, comparaison, dégâts, effets de fin de round.
  Vectorisé numpy.
- **Repli obligatoire** vers le moteur, cellule par cellule, dès qu'une capacité en jeu dépend des
  pillz : `Bet >/< N`, `per Pillz Left`, `Recover`, `Tune Out`, et les conditions `Killshot` / `Perfect`
  (qui dépendent du rapport des attaques).
- **Test qui autorise le raccourci** : balayage façon `scripts/engine_crash_sweep.py` sur toutes les
  descriptions gérées — matrice rapide identique, cellule à cellule, à `engine.step`.

### Étape 3 — Solveur exact de fin de partie (3-5 j)

- `equilibrium.py` : Nash d'un jeu matriciel à somme nulle par programmation linéaire
  (`scipy.optimize.linprog`) et **forme séquentielle** pour le cas « carte visible, pillz cachées »
  (le second joueur a une stratégie par carte révélée). Tests : pile ou face → 50/50, équilibre pur
  connu, jeu symétrique → valeur 0.
- `solver.py` : induction arrière mémoïsée sur une clé canonique (round, vies, pillz, cartes restantes,
  effets persistants, premier joueur). Round 4 exact (ms), round 3 exact (~0,1 s avec l'étape 2).
- Livrables : une stratégie `solver` **parfaite sur les deux derniers rounds** — donc déjà imbattable
  en fin de partie — exposée dans `STRATEGIES` et `/ai_pick`, et un **oracle** pour tester le reste.

### Étape 4 — Recherche à profondeur limitée + valeur apprise (1-2 semaines)

- **Abstraction des mises** : grille (0, 1, 2, 3, 4, 6, 8, tout + variantes fury) au lieu de 0..12,
  affinée autour du coup retenu ; le round 2 tombe de ~14 000 à ~4 000 feuilles.
- **V̂(état)** : régression sur les valeurs exactes du solveur (rounds 3-4), puis amorçage : les cibles
  des rounds 1-2 viennent de la recherche qui utilise V̂.
  - Traits : round, premier joueur, vies, pillz, et par carte étoiles / puissance / dégâts / bonus actif,
    plus les `Capacity` **déjà structurées par le parseur** (type, valeur, borne, conditions).
  - Modèle : gradient boosting ou petit MLP torch ; commencer par un modèle linéaire comme référence.
- `policy.nash_pick` : construit le sous-jeu, le résout, **tire au sort dans la stratégie mixte**
  (graine pour la reproductibilité), conditionne la réponse du second joueur à la carte révélée.
- Budget : < 1 s par décision dans l'interface, réglable (profondeur, finesse de la grille).

### Étape 5 — Prouver l'invincibilité (en parallèle des étapes 3-4)

- **`scripts/exploitability.py`** : calculer la meilleure réponse à notre politique dans le jeu abstrait
  → « combien un adversaire parfait gagne contre nous ». C'est la mesure du but ; elle doit tendre vers 0.
  Publier la courbe à chaque version.
- Échelle ELO interne (`scripts/ai_arena.py`) : aléatoire, heuristique, glouton, minimax, solveur de fin
  de partie, politique Nash, **version précédente** (garde-fou anti-régression).
- **Fidélité des règles** : un solveur exploite les bugs du moteur autant que les erreurs adverses.
  Chaque combat ELO importé (`docs/ORACLE.md`, `tests/test_ur_battles.py`) est une vérification de plus ;
  viser d'abord les capacités du pool ELO et les points non tranchés (cycles de Stops, Team du Leader,
  Tune Out + fury, Mindwipe/Combust). Les 10 descriptions non gérées restent hors des mains jouées.

### Étape 6 — Punir les adversaires réels (après le Nash)

- `exploit.py` : modèle d'adversaire (distribution de ses mises selon le round, son budget, la carte
  qu'il voit), alimenté par les combats ELO capturés et par les parties jouées dans l'interface.
- **Meilleure réponse sûre** : jouer la meilleure réponse au modèle en bornant la perte par rapport à
  la valeur de Nash (*restricted Nash response*) — on exploite sans redevenir exploitable si le modèle
  se trompe. C'est ce qui fait passer de « jamais battu » à « gagne presque à chaque fois ».

### Phase 2 — composer le deck (hors périmètre aujourd'hui, préparé par ce plan)

Le solveur donne la **valeur d'équilibre d'un affrontement de mains**. Évaluer un deck de 8 cartes,
c'est moyenner cette valeur sur les tirages 4 parmi 8 des deux camps, face au méta ELO. Rien à
réarchitecturer : il suffira de brancher un optimiseur (recherche locale sous contrainte d'étoiles et
de bans) sur `solver.value(main_a, main_b)`.

### Ce qui n'est pas retenu, et pourquoi

Le self-play PPO/DQN « nu » de la ROADMAP § E : dans un jeu à coups simultanés, il converge vers une
politique déterministe **exploitable** — l'inverse du but. Les variantes qui convergent vraiment
(NFSP, PSRO, R-NaD/DeepNash) restent en réserve si la taille du jeu résiste, mais ici le jeu est petit :
**résoudre est plus simple et plus fort qu'apprendre**. Gymnasium reste un emballage utile pour
expérimenter, pas le cœur.

## Vérification

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python -m pytest -q                      # 450 tests aujourd'hui
.venv/bin/python scripts/engine_crash_sweep.py     # 0 exception
.venv/bin/python scripts/capacity_coverage.py | head -1
.venv/bin/python scripts/bench_engine.py           # débit moteur, coût d'une décision
.venv/bin/python scripts/ai_arena.py --games 200   # échelle entre stratégies
.venv/bin/python scripts/exploitability.py         # (étape 5) LE critère : ε → 0
```

Tests à écrire, dans l'esprit du dépôt (attentes calculées à la main) :

- `equilibrium` : jeux matriciels de référence (pile ou face → 50/50, équilibre pur, symétrie → 0).
- `round_matrix` : identité cellule à cellule avec `engine.step` sur toutes les capacités gérées.
- `solver` : sur des fins de partie minuscules, valeur trouvée = valeur calculée à la main (ex. dernier
  round, 1 vie contre 2, 3 pillz contre 0) ; la politique optimale bat toute stratégie fixe dans ce sous-jeu.
- `policy` : distribution sur des coups légaux, reproductible à graine fixée, strictement mixte là où
  elle doit l'être.
- Bout en bout : une partie ELO complète dans l'interface contre l'adversaire « nash » avant de déclarer
  le chantier fini (convention du dépôt).

## Risques et points à confirmer

1. ~~**La règle d'information**~~ → confirmée le 2026-09-17 : le second joueur voit toujours la carte,
   jamais les pillz. Le solveur devra donc résoudre un jeu en forme séquentielle, pas une simple matrice.
2. ~~**Le pool ELO**~~ → sans effet sur le jeu de l'IA ; à reprendre en phase 2 (composition de deck).
3. **Le chemin analytique de l'étape 2** : c'est lui qui rend le solveur possible. S'il ne tient pas
   pour trop de capacités, il faudra un moteur de round dédié (numpy, sans objets) — plus de travail,
   même résultat.
4. **Les règles encore incertaines** : le solveur amplifie les erreurs du moteur ; l'oracle doit grossir
   au même rythme que l'IA.
5. **Temps de calcul dans l'interface** : profondeur et finesse de grille sont les deux boutons à tourner.
