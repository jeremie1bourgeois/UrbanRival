# Plan d'exécution du moteur Rust (document vivant)

Le plan **actuel** pour construire le moteur rapide : la référence du moment, pas un cadre imposé. Il se modifie à
tout moment (étapes ajoutées, retirées, réordonnées) dès qu'une mesure, une difficulté ou une meilleure idée le
justifie ; quand la réalité s'écarte du plan, on corrige le plan plutôt que de forcer le code à le suivre. Cap et
principes : [MOTEUR-RUST.md](MOTEUR-RUST.md).

Ce document dit **ce qu'on compte faire**. **Où on en est** se lit dans [UrbanRust/README.md](../UrbanRust/README.md) :
ce qui est fait, comment le code est organisé, chaque optimisation et sa raison. À la fin de chaque étape : statut mis
à jour ici, mesure au journal, état mis à jour là-bas.

Statuts : ⬜ à faire · 🟨 en cours · ✅ fait. Chaque étape laisse les tests verts.

## Ce qu'on compte

- **Branche** : un couple de coups simulé, c'est-à-dire une case de matrice.
- **Nœud** : un état dont on calcule la valeur.
- Indicateurs : branches par seconde et par cœur ; nœuds par seconde ; temps pour résoudre un état selon le round de
  départ (4, 3, 2 ou 1) ; mémoire utilisée.
- Point de départ (moteur Python, [IA.md § 5.3](IA.md)) : ~1 000 branches/s ; résoudre depuis le round 3 prend
  ~1 min, depuis le round 2 ~4 h et la partie entière ~3 jours (ces deux derniers chiffres sont extrapolés).
- Cibles de départ, à ajuster après les premières mesures : **1 million de branches/s par cœur** avec le round
  simple, **10 millions** avec le bloc de mises (étape 1.4).

## Phase 1 — Construire, optimisé dès la conception

Objectif : un moteur Rust qui joue un round exactement comme le Python, pensé pour la vitesse dès la première ligne ;
puis le solveur de matrices et la recherche exacte.

**Règles de conception, dès le départ** (les changer plus tard coûterait une réécriture) :
- état compact, copiable, sans allocation (déjà en place dans `UrbanRust/src/contract.rs`) ;
- capacités réduites à des nombres et des masques : aucun texte, aucune table de hachage pendant un round ;
- aucune allocation pendant un round ;
- pas de journal des effets : celui du Python sert l'interface, pas le calcul ;
- la résolution d'un round en **deux étages** : d'abord ce qui ne dépend que des deux cartes jouées, ensuite ce qui
  dépend des mises (attaque, fury, Killshot, pillz restantes, vainqueur). Le premier étage se calcule une fois pour
  toutes les combinaisons de mises d'une même paire de cartes ; quand une capacité dépend de la mise
  (« Bet > N »), une fois par tranche de mises.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 1.1 | Lecteur du corpus en Rust : lire les familles générées par `scripts/build_engine_corpus.py` | les 8 familles sont lues et leurs empreintes égalent celles de `data/engine_digests.json` | ✅ |
| 1.2 | Résolution d'un round, famille par famille (solo, interactions, planchers, persistants, leaders, oculus, combat, aleatoire) | chaque famille identique à 100 % ; au bout, tout le corpus (~113 500 rounds) | 🟨 |
| 1.3 | Coups légaux et fin de partie | mêmes résultats que `reference.py` | ⬜ |
| 1.4 | Bloc de mises : toutes les combinaisons de mises d'une paire de cartes, premier étage calculé une fois | chaque case égale au round simple | ⬜ |
| 1.5 | Test « zéro allocation » sur un round et sur un bloc | le test passe | ⬜ |
| 1.6 | Solveur de matrices : solution pure, sinon simplexe ; chaque solution vérifiée par son écart à l'équilibre | exemple d'IA.md § 4.4 ; matrices aléatoires égales à SciPy (valeurs attendues écrites par un script Python) | ⬜ |
| 1.7 | Les équilibres d'une matrice : la matrice elle-même, qui décrit exactement l'ensemble de ses équilibres, et un équilibre explicite par coup — celui qui lui donne la plus forte probabilité (une résolution par coup, en repartant de la solution trouvée) | sur des matrices à équilibres multiples connus (coups en double, égalités), chaque équilibre renvoyé passe le vérificateur et chaque coup jouable dans un équilibre apparaît | ⬜ |
| 1.8 | Le maximum : tous les équilibres « coins » de chaque joueur (tout autre équilibre est un mélange de coins), en partant de la solution trouvée et en visitant les solutions voisines de même valeur ; un plafond, signalé quand il est atteint | sur les mêmes matrices, la liste complète des coins est retrouvée ; nombre de coins mesuré sur des matrices réelles | ⬜ |
| 1.9 | Solveur Python de référence, lent (`reference.py` + SciPy), sur quelques dizaines d'états de rounds 4 et 3 | fichier de valeurs attendues versionné | ⬜ |
| 1.10 | Recherche exacte avec mémo : depuis le round 4, puis 3, puis 2 | mêmes valeurs que la référence Python ; **premier palier** atteint (rounds 3-4) | ⬜ |
| 1.11 | Parallélisme sur les cœurs (`rayon`), entre états indépendants | mêmes valeurs qu'en un seul fil ; accélération mesurée | ⬜ |

## Phase 2 — Stabiliser

Objectif : un moteur sur lequel on peut compter avant de le mesurer.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 2.1 | Élargir le corpus avec des rounds tirés au hasard (mains de `src/core/engine/hands.py`, états issus de parties jouées au hasard) | Rust identique à Python sur le corpus élargi | ⬜ |
| 2.2 | Contrôles automatiques pendant la recherche, en mode test : chaque matrice vérifiée, valeurs dans [0, 1], échanger les camps donne `1 − V` (hors asymétries connues, `KNOWN_ASYMMETRIES`) | contrôles en place | ⬜ |
| 2.3 | Lancer des milliers de résolutions depuis le round 3 sur des mains au hasard ; tout écart trouvé devient un cas du corpus | aucune alerte ni plantage sur 10 000 résolutions | ⬜ |

## Phase 3 — Mesurer

Objectif : savoir combien de temps prend chaque palier, avec des chiffres comparables d'une version à l'autre.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 3.1 | Banc d'essai fixe et versionné : un même lot de paires de mains et d'états de départ aux rounds 4, 3, 2 et 1 | le banc existe | ⬜ |
| 3.2 | Programme de mesure qui affiche les indicateurs (§ Ce qu'on compte) ; benchmarks `criterion` pour le round, le bloc et la matrice | une commande donne tous les chiffres | ⬜ |
| 3.3 | Mesurer sur le Mac M4 et sur un serveur multicœur | temps connu pour chaque palier (la partie entière éventuellement extrapolée) ; chiffres au journal | ⬜ |

## Phase 4 — Comprendre où on perd du temps, puis accélérer

Objectif : la boucle qui fait gagner du temps, répétée tant qu'elle rapporte.

**La boucle** : profiler → choisir le plus gros poste → une seule optimisation → re-mesurer sur le banc → tests de
référence verts et mêmes valeurs → journal. Une optimisation qui ne fait rien gagner est retirée.

**Les outils** :
- `samply` pour voir dans quelles fonctions part le temps ;
- des compteurs internes : branches, nœuds, matrices par taille, part des solutions pures, réussites de la mémo,
  temps par poste (moteur, mémo, solveur).

**Les pistes probables**, dans un ordre que le profil confirmera ou non :
- pousser le premier étage du bloc de mises au maximum ;
- la mémo : hachage rapide, clé compacte, taille maîtrisée ;
- ne pas résoudre deux fois des états équivalents (cartes en double, vies ou pillz qui ne peuvent plus servir),
  chaque équivalence prouvée par un test ;
- le solveur : actions dominées, cas fréquents ;
- la disposition en mémoire et les calculs vectorisés sur la grille des mises.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 4.1 | Premier profil complet sur le banc | les trois plus gros postes sont nommés au journal | ⬜ |
| 4.2 | Boucle d'optimisation | **palier visé** atteint : un état de début de round 2 résolu jusqu'à la fin en quelques secondes sur un serveur multicœur | ⬜ |
| 4.3 | Tenter la partie entière | temps mesuré pour une paire de mains ; on décide alors si l'idéal est à portée | ⬜ |

## Après ce plan

- Liaison Python (`pyo3`) : FastAPI et l'entraînement appellent le moteur.
- Générateur de datasets : rounds 3-4, puis rounds 2-4. Chaque exemple garde la valeur, la matrice de sa décision
  (tous les équilibres) et ses équilibres explicites (étapes 1.7 et 1.8).
- Le modèle, appelé depuis Rust, pour la décision du round 1.

## Points d'attention

- Les règles encore ouvertes (R1 surtout, un ordre de résolution ; [REGLES.md](REGLES.md), registre) peuvent
  changer le moteur Python ; on régénère alors le corpus et le moteur Rust suit.
- Un jeu peut avoir plusieurs équilibres : les tests comparent les **valeurs**, pas les stratégies.
- Deux coups « aussi bons » l'un que l'autre ne le sont qu'à une tolérance près (les valeurs sont des flottants) :
  sans cette tolérance, des équilibres valables seraient écartés.
- Garder les matrices pèse : ~20 Ko par exemple de round 2 (3 matrices d'au plus 23 × 69 en f32), soit ~20 Go par
  million d'exemples.
- La mémo de la partie entière peut peser plusieurs Go : à surveiller dès la phase 3.

## Journal des mesures

| Date | Machine | Mesure | Valeur |
|---|---|---|---|
| 2026-09-18 | Mac (moteur Python) | branches par seconde | ~1 000 (IA.md § 10) |
| 2026-10-09 | PC Windows x86_64 | relire tout le corpus (113 540 entrées, 29 365 decks) puis le réécrire et l'empreinter (`tests/lecture_corpus.rs`, profil de test) | 35 s sans optimisation ; 5 s avec la crate en -O1 et les dépendances en -O3 |
