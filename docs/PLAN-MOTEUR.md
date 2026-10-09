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
| 1.2 | Résolution d'un round, famille par famille (solo, interactions, planchers, persistants, leaders, oculus, combat, aleatoire) | chaque famille identique à 100 % ; au bout, tout le corpus (~113 500 rounds) | ✅ |
| 1.3 | Coups légaux et fin de partie | mêmes résultats que `reference.py` | ✅ |
| 1.4 | Bloc de mises : toutes les combinaisons de mises d'une paire de cartes, premier étage calculé une fois | chaque case égale au round simple | ✅ |
| 1.5 | Test « zéro allocation » sur un round et sur un bloc | le test passe | ✅ |
| 1.6 | Solveur de matrices : solution pure, sinon simplexe ; chaque solution vérifiée par son écart à l'équilibre | exemple d'IA.md § 4.4 ; matrices aléatoires égales à SciPy (valeurs attendues écrites par un script Python) | ✅ |
| 1.7 | Les équilibres d'une matrice : la matrice elle-même, qui décrit exactement l'ensemble de ses équilibres, et un équilibre explicite par coup — celui qui lui donne la plus forte probabilité (une résolution par coup, en repartant de la solution trouvée) | sur des matrices à équilibres multiples connus (coups en double, égalités), chaque équilibre renvoyé passe le vérificateur et chaque coup jouable dans un équilibre apparaît | ✅ |
| 1.8 | Le maximum : tous les équilibres « coins » de chaque joueur (tout autre équilibre est un mélange de coins), en partant de la solution trouvée et en visitant les solutions voisines de même valeur ; un plafond, signalé quand il est atteint | sur les mêmes matrices, la liste complète des coins est retrouvée ; nombre de coins mesuré sur des matrices réelles | ✅ |
| 1.9 | Solveur Python de référence, lent (`reference.py` + SciPy), sur quelques dizaines d'états de rounds 4 et 3 | fichier de valeurs attendues versionné | ✅ |
| 1.10 | Recherche exacte avec mémo : depuis le round 4, puis 3, puis 2 | mêmes valeurs que la référence Python ; **premier palier** atteint (rounds 3-4) | ✅ |
| 1.11 | Parallélisme sur les cœurs (`rayon`), entre états indépendants | mêmes valeurs qu'en un seul fil ; accélération mesurée | ✅ |

## Phase 2 — Stabiliser

Objectif : un moteur sur lequel on peut compter avant de le mesurer.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 2.1 | Élargir le corpus avec des rounds tirés au hasard (mains de `src/core/engine/hands.py`, états issus de parties jouées au hasard) | Rust identique à Python sur le corpus élargi | ✅ |
| 2.2 | Contrôles automatiques pendant la recherche, en mode test : chaque matrice vérifiée, valeurs dans [0, 1], échanger les camps donne `1 − V` (hors asymétries connues, `KNOWN_ASYMMETRIES`) | contrôles en place | ✅ |
| 2.3 | Lancer des milliers de résolutions depuis le round 3 sur des mains au hasard ; tout écart trouvé devient un cas du corpus | aucune alerte ni plantage sur 10 000 résolutions | ✅ |
| 2.4 | Corriger le solveur sur les matrices réelles du round 2 riches en pillz : le simplexe y rend une stratégie à ~1e-3 de l'équilibre (13 × 57, recherche depuis le round 1 de `masse/partie-0` et `partie-1`) ; la vérification l'arrête net, la recherche plante | la matrice fautive devient un test ; ces deux recherches vont au bout | ✅ |

## Phase 3 — Mesurer

Objectif : savoir combien de temps prend chaque palier, avec des chiffres comparables d'une version à l'autre.

| # | Étape | Fini quand | Statut |
|---|---|---|---|
| 3.1 | Banc d'essai fixe et versionné : un même lot de paires de mains et d'états de départ aux rounds 4, 3, 2 et 1 | le banc existe | ✅ |
| 3.2 | Programme de mesure qui affiche les indicateurs (§ Ce qu'on compte) ; benchmarks `criterion` pour le round, le bloc et la matrice | une commande donne tous les chiffres | ✅ |
| 3.3 | Mesurer sur le Mac M4 et sur un serveur multicœur | temps connu pour chaque palier (la partie entière éventuellement extrapolée) ; chiffres au journal | 🟨 |

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
| 4.1 | Premier profil complet sur le banc | les trois plus gros postes sont nommés au journal | ✅ |
| 4.2 | Boucle d'optimisation | **palier visé** atteint : un état de début de round 2 résolu jusqu'à la fin en quelques secondes sur un serveur multicœur | 🟨 |
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
| 2026-10-09 | PC Windows, i7-8750H, un cœur | round simple (version de référence lisible), tout le corpus rejoué 30 fois en release ; mesure informelle, avant le banc de la phase 3 | ~2,8 millions de rounds/s (~360 ns par round) : la cible de départ du round simple (1 million/s par cœur) est déjà dépassée |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | coups légaux des deux camps et fin de partie, sur les états du corpus `aleatoire`, en release ; mesure informelle | ~58 ns par état (~71 coups, < 1 ns par coup) : négligeable devant un round |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | premier étage du round (jusqu'au niveau 2 puissance / dégâts) seul, tout le corpus en release, meilleure de 7 séries | ~236 ns sur ~385 ns, soit ~60 % du round |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | bloc de mises contre round simple, mêmes cases, release : blocs de `aleatoire` (854 191 cases) et tout le corpus (29 millions) ; machine chargée, le rapport compte plus que l'absolu | gain x2,3 par case (`aleatoire` : 500 → 216 ns ; corpus : 448 → 198 ns, ~5 millions de cases/s). Cible de départ du bloc (10 millions/s) pas atteinte : phase 4 |
| 2026-10-09 | PC Windows, i7-8750H | allocations pendant un round (tout le corpus), un bloc de mises (blocs d'`aleatoire` et blocs à condition Bet), les coups légaux et la fin de partie (`tests/sans_allocation.rs`), en debug et en release | 0 |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | solveur de matrices (point-selle, sinon simplexe avec la règle de Bland), matrices aléatoires de `data/nash_expected.json`, release, meilleure de 5 séries ; mesure informelle | 4 × 4 : < 1 µs ; 23 × 23 : ~29 µs ; 23 × 92 : ~320 µs, presque autant que les ~2 100 cases de moteur de la même matrice (~420 µs) : à surveiller dès la phase 3 |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | équilibres par coup (`Solver::equilibria` : deux simplexes, puis une optimisation par coup en repartant de l'optimum), matrices de `data/nash_expected.json`, release ; mesure informelle | 3 à 5 fois `solve` : 23 × 23 ~105 µs, 23 × 92 ~1,3 ms ; une fois par décision, pour les datasets |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | coins des stratégies optimales (`Solver::corners`) sur des matrices réelles : les matrices du round 4 (un bloc, cases exactes 0 / ½ / 1 par `terminal`) des états de `aleatoire` (233) et de `solo` (13 056), release | toutes à point-selle ; coins par joueur : `aleatoire` 1 dans 227 listes sur 466, jusqu'à 19 ; `solo` jusqu'à 9 (5 le plus souvent) ; aucune liste tronquée (plafond 256) ; ~5 à 15 µs par matrice |
| 2026-10-09 | PC Windows, i7-8750H, Python 3.10, un cœur | solveur Python de référence (`scripts/build_search_expected.py` : `reference.step` + SciPy, mémo par état) sur 68 états : 30 du round 4, 38 du round 3 (dont 10 aux plus gros stocks de pillz et 8 jumeaux) | round 4 : < 0,1 s par état ; round 3 : 15 s en moyenne (jusqu'à ~145 s), 239 états distincts résolus en moyenne (jusqu'à 715) ; ~17 min en tout |
| 2026-10-09 | PC Windows, i7-8750H, un cœur | recherche exacte avec mémo (`search::Search`, un seul fil, `HashMap` standard), release ; états de `data/search_expected.json` et du round 2 de `aleatoire` | round 4 : < 1 ms ; round 3 : 4 ms en moyenne, 25 ms au plus (Python : 15 s en moyenne, jusqu'à ~145 s) ; round 2 : 0,14 s en moyenne (8 états à intervalle régulier), 1,8 s en moyenne et 2,5 s au plus pour les 3 plus riches en pillz (13 et 11 ; ~43 000 états résolus ; Python : ~4 h extrapolées). **Premier palier atteint** ; le palier visé (rounds 2-4) est à portée d'un seul cœur |
| 2026-10-09 | PC Windows, i7-8750H, 6 cœurs / 12 fils | recherche répartie sur les cœurs (`Search::parallel`, rayon, mémo partagée en 64 morceaux), release, mêmes valeurs qu'en un seul fil | un état du round 2 : x4,3 (0,193 → 0,045 s) et x4,5 pour les plus riches (2,19 → 0,49 s) ; 60 états du round 2 indépendants, chacun sa recherche : x4,4 (8,36 → 1,90 s). Sur un fil, ~20 % plus lent qu'à l'étape 1.10 (mémo à verrous, empreinte calculée deux fois ?) : à confirmer sur le banc de la phase 3 |
| 2026-10-09 | PC Windows, i7-8750H, Python 3.10 | corpus élargi (étape 2.1) : famille `masse`, 2 000 parties jouées au hasard avec les mains de `hands.py`, de nuit une fois sur deux (graine 1) | 37 665 rounds générés en 63 s ; 82 % des 7 868 niveaux de cartes tirables (2 485 noms sur 2 494), 22 des 30 textes « Night: » joués de nuit ; Rust identique au Python du premier coup, rounds et blocs (24 374 blocs, ~5,7 millions de cases) ; `tests/bloc.rs` passe de ~11 à ~18 s |
| 2026-10-09 | PC Windows, i7-8750H, 6 cœurs | échanger les camps (étape 2.2) : chaque état résolu depuis 2 011 états de départ (les 68 de `search_expected.json`, tous ceux du round 3 de `masse`, 40 de son round 2) revu de l'autre camp par une recherche sur le deck miroir, release ; exploration ponctuelle | 501 157 états contrôlés, aucun écart à 1 − V (tolérance 1e-9) ; 14 états n'ont pas de miroir exact parmi ceux du miroir : les mêmes effets dans un autre ordre (Poison et Heal, Heal et Toxine), l'asymétrie connue, sans effet sur la valeur. ~9 s en tout |
| 2026-10-09 | PC Windows, i7-8750H, 6 cœurs | 10 000 résolutions depuis le round 3 (étape 2.3), mains au hasard de jour comme de nuit (`scripts/build_search_states.py`, 75 s en Python), sous les contrôles de l'étape 2.2, profil de test ; machine chargée, mesure informelle | premier passage : 4 alertes, deux règles du moteur Python qui dépendaient du camp (3 doubles KO, 1 ordre de deux pertes au niveau 3), tranchées et corrigées ; ensuite aucune alerte ni plantage. 640 154 états résolus (au plus 1 076 par résolution), 376 valeurs fractionnaires ; 1,8 s, 4,1 s avec le contrôle miroir |
| 2026-10-09 | PC Windows, i7-8750H, 6 cœurs | partie entière depuis le round 1, mesure exploratoire (`Search::parallel`, release) : 3 mains de `masse` (parties 0 à 2), 8 464 branches au round 1, chacun des ~5 500 à 6 000 états du round 2 résolu dans une mémo partagée | 24 s, 46 s et 31 s par main ; 0,7 à 2 millions d'états en mémo (114 octets par état, soit ~100 à 300 Mo) : la partie entière paraît à portée (Python : ~3 jours extrapolés). Mais le solveur plante sur un état du round 2 dans 2 mains sur 3 (étape 2.4) |
| 2026-10-09 | Mac M4, 10 cœurs | étape 2.4 : 1 934 matrices mixtes réelles du round 2 (60 états de `masse`), le simplexe suivi en arithmétique exacte ; puis la partie entière depuis le round 1 (`Search::parallel`, release) sur 10 mains de `masse` (parties 0 à 9) | faux non-zéros jusqu'à 1,5e-11, vrais coefficients candidats au moins 1,4e-3 : seuil de pivot à 1e-9. Les 10 mains vont au bout : 8,6 à 19 s par main (13 s en moyenne), 0,6 à 2 millions d'états en mémo |
| 2026-10-09 | Mac M4, 10 cœurs (4 performance, 6 efficacité) | banc d'essai (`cargo run --release --example banc`) : les 24 parties de `data/engine_bench.json`, chaque état résolu par sa propre recherche ; le round 1 sur les 4 premières | round 4 : 1,7 µs par état ; round 3 : 0,15 ms (1,3 ms au plus) ; round 2 : 53 ms sur un fil (0,31 s au plus), 13 ms sur 10 fils (x4,1), 7 800 nœuds et 279 000 branches par état ; partie entière : 9,6 s par main (12,4 s au plus), 0,9 million de nœuds et 142 millions de branches par main, mémo jusqu'à 235 Mo. Branches par seconde et par cœur : 4,6 à 6,7 millions sur un fil, 1,5 à 2,2 millions sur 10 fils ; 64 s de temps système pour 248 s de calcul. Le palier visé (un début de round 2 en quelques secondes) est déjà tenu sur le M4 pour ces états |
| 2026-10-09 | Mac M4, un cœur | `cargo bench` (criterion) : toutes les cases des 96 états du banc (~226 000), en round simple et en bloc de mises ; les 104 matrices de `data/nash_expected.json` | round simple 176 ns par case (5,7 millions/s) ; bloc 73 ns (13,6 millions/s), x2,4 : la cible de départ du bloc (10 millions/s par cœur) est atteinte sur cette machine ; solveur : les 104 matrices en 857 µs |
| 2026-10-09 | Mac M4, 10 cœurs, chargé | premier profil (étape 4.1) : `sample` (macOS, un relevé par ms) sur le banc, temps propre par fonction, l'attente de travail des fils de rayon exclue ; round 3 sur un fil, round 2, partie entière sur 10 fils. Le round et le solveur sont inlinés dans `Search::value` : leur part se déduit de criterion (73 ns par case de bloc) | les trois plus gros postes : **1. les verrous de la mémo**, ~45 % du temps actif de la partie entière sur 10 fils (absents sur un fil) ; **2. le hachage SipHash de l'état**, deux fois par consultation de la mémo : 25 % sur un fil, 31 % sur 10 fils ; **3. le round** (bloc de mises, le niveau 2 en tête avec 14 % sur un fil) : ~40 à 50 % sur un fil. Puis les copies d'états (memmove, ~5 %) et les allocations (~3 %) |
| 2026-10-09 | Mac M4, 10 cœurs, chargé (charge ~12) | étape 4.2, hachage de l'état regroupé en mots de 64 bits (effets actifs seulement) : 139 → 12 ns par état (SipHash, 105 693 états réels) ; banc, A/B en alternance, meilleur de 3 (partie entière : de 2) | round 2 : 57,0 → 36,6 ms sur un fil (x1,56), 15,5 → 8,9 ms sur 10 fils (x1,74) ; round 3 : 152 → 135 µs (x1,13) ; partie entière : 13,3 → 9,3 s (x1,43) ; round 4 dans le bruit (~1,7 µs). Mêmes empreintes de valeurs. La machine chargée rend les chiffres absolus instables d'un passage à l'autre (round 2 de référence : 53 puis 78 ms) : seules les comparaisons en alternance comptent |
| 2026-10-09 | Mac M4, 10 cœurs, chargé | étape 4.2, la mémo : consultations comptées par round de l'état cherché (compteurs temporaires) ; puis variantes de verrou en A/B, en alternance | partie entière : 49 millions de consultations d'états du round 4 (98,9 % trouvés), 5,2 millions du round 3 (96,9 %), 8 464 du round 2 (36,5 %) ; 24 débuts du round 2 : 1,9 million du round 4 (91 %), 20 000 du round 3 (20 %). Gardée : `RwLock` au lieu de `Mutex`, partie entière x1,34, x1,42 puis x1,38 en trois séances (13,0 → 9,4 s), le reste dans le bruit (±15 %). Écartées : 1 024 morceaux au lieu de 64 (partie entière x1,10, rien de plus avec le `RwLock`, et une recherche du round 4 passe de 1,3 à 3,4 µs : la mémo coûte à créer) ; répartir sur les cœurs jusqu'au round 2 seulement au lieu de 3 (x1,05, rien de net). Garder la mémo pour le round 4 : sans elle, ~49 millions de résolutions au lieu de ~0,5 million |
| 2026-10-09 | Mac M4, 10 cœurs | partie entière, version d'avant la phase 4 contre celle d'après le `RwLock`, A/B en alternance, meilleur de 3 (charge ~4 au départ) | 8,77 → 3,55 s par main (x2,47) : le gain cumulé du hachage regroupé et du `RwLock` |
| 2026-10-09 | Mac M4, 10 cœurs | profil sans LTO (`CARGO_PROFILE_RELEASE_LTO=false`, 16 unités de code, pour l'attribution seulement) ; nœuds et branches par round d'une partie entière | le round domine : second étage 20-24 %, niveau 2 14-19 %, boucle du bloc 10-16 %, copies d'états 7-8 % ; le solveur ~2 %. Sur 10 fils s'y ajoutent la latence mémoire des consultations de la mémo (comparaison d'états, 17 %) et le hachage restant (~13 %). Une partie entière : 90 à 200 millions de branches, ~1 million de matrices ; au round 3, 313 à 469 branches par nœud, au round 4, 63 à 116 |
| 2026-10-09 | Mac M4, un cœur puis 10 | niveau 2 sans travail inutile (sortie immédiate si aucune capacité ne touche les stats demandées) | criterion : bloc 16,9 → 13,1 ms sur les cases du banc (13,4 → 17,3 millions de cases/s), round simple −14 % ; banc A/B : round 4 x1,30, round 3 x1,16, round 2 x1,13 (x1,08 sur 10 fils), partie entière 3,91 → 3,57 s (x1,10) |
| 2026-10-09 | Mac M4, un cœur | Killshot et Perfect sautés quand aucune capacité ne porte ces conditions ; criterion contre le commit précédent | bloc 16,9 → 17,5 millions de cases/s (+2,8 %), round simple +2,1 %. Ordre de grandeur de la partie entière : ~142 millions de cases à ~17 millions/s par cœur font ~1,3 s sur 10 cœurs, pour 3,5 s mesurées : sur tous les cœurs, la mémo (50 à 100 millions de consultations) pèse plus que le round |
| 2026-10-09 | Mac M4, chargé (charge 10 à 17) | mémo hachée par un hacheur multiplicatif au lieu de SipHash ; banc A/B en alternance | round 2 : 29,8 → 26,2 ms sur un fil (x1,14), x1,08 sur 10 fils ; round 3 x1,05 ; partie entière x0,96 (2 passages) puis x1,07 (3 passages) : dans le bruit. Sur tous les cœurs, l'empreinte n'est plus ce qui limite la mémo, c'est l'accès lui-même |
| 2026-10-09 | Mac M4 | verrous de la mémo sur un fil : essai jetable sans aucun verrou (non gardé) | aucun gain mesurable (round 3 x1,00, round 2 26,2 ms dans les deux cas) : un verrou jamais disputé ne coûte rien ici |
| 2026-10-09 | Mac M4 | sur un fil, valeurs des états suivants calculées pendant le bloc ; banc A/B, meilleur de 5 | round 3 : 94,6 → 90,6 µs (x1,04) ; round 2 : 26,2 → 25,3 ms (x1,04) sur un fil, 6,0 → 5,7 ms (x1,05) sur 10 fils |
| 2026-10-09 | Mac M4, un cœur | ce que coûte une case de bloc : essais jetables sur criterion, le bloc privé d'une partie du second étage ; puis compteurs sur 6,7 millions de cases (24 débuts du round 2) | case entière 58 ns ; sans second étage 15 ns (la mécanique du bloc, copies comprises : ~26 %) ; niveau 3 ~19 %, niveau 4 ~20 %, Tune Out ~5 %, le reste du second étage ~31 %. Joueurs en vie après le combat dans 80 % des cases ; parmi elles, 53 % sans capacité restante ni effet actif, 8 % avec des effets seulement |
| 2026-10-09 | Mac M4 | niveaux 3 et 4 sautés quand il n'y a rien à y faire | criterion : bloc 17,2 → 20,0 millions de cases/s (+14 %) ; banc A/B : round 3 x1,03, round 2 x1,04 sur un fil et x1,05 sur 10 fils, partie entière dans le bruit (x0,98) : la recherche dilue le gain des cases |
| 2026-10-09 | Mac M4, un cœur | niveau 2, un seul tri des capacités pour les trois cibles ; criterion en alternance (deux binaires compilés à part, 3 passages chacun : une mesure contre une base enregistrée plus tôt s'est révélée faussée par la charge) | bloc 19,3-19,5 → 21,3-21,6 millions de cases/s (+10 %) ; banc A/B : round 2 25,2 → 23,4 ms sur un fil (x1,08), round 3 x1,02 |
| 2026-10-09 | Mac M4 | la recherche sans allocation par état résolu, sauf le vecteur de ses valeurs (réservé d'emblée) ; banc A/B, meilleur de 4 | round 3 : 84,2 → 77,8 µs (x1,08) ; round 2 : 23,0 → 21,9 ms sur un fil (x1,05), 5,2 → 4,6 ms sur 10 fils (x1,13) |
| 2026-10-09 | Mac M4 | signature des mises sur les seules conditions « Bet » réelles ; criterion en alternance, banc A/B | bloc 21,1-21,6 → 22,7-23,8 millions de cases/s (+7 %) ; round 3 : 76,1 → 70,8 µs (x1,07) ; round 2 : 21,6 → 20,3 ms (x1,06) sur un fil |
| 2026-10-09 | Mac M4, un cœur | Tune Out cherché d'un coup d'œil avant d'être consommé (retiré) ; criterion en alternance, 3 passages | aucun gain (23,5-24,8 contre 23,8-25,0 millions de cases/s) : l'essai sans Tune Out (~5 %) mesurait le retrait de la vérification, pas son coût évitable |
| 2026-10-09 | Mac M4, 10 cœurs | réparti sur les cœurs, chercher d'abord en mémo les états suivants sur le fil courant et n'envoyer aux cœurs que les inconnus (retiré) ; banc A/B, meilleur de 3 | partie entière 2,66 → 2,60 s (x1,02), round 2 dans le bruit : les tâches rayon des états déjà connus ne coûtaient presque rien |
| 2026-10-09 | Mac M4, 10 cœurs | cache par fil à correspondance directe devant la mémo partagée, 1 024, 4 096 ou 16 384 cases (essais, non gardé) | partie entière x1,13 au premier passage, puis x1,01 (1 024 et 4 096) et x0,87 (16 384) : le premier gain était du bruit ; les mesures sur 10 fils varient de ±10 % sur cette machine |
| 2026-10-09 | Mac M4 | plafond d'une mémo compacte : essai jetable indexé par la seule empreinte de 64 bits (16 octets par entrée au lieu de 128, en plus de la table habituelle) | partie entière x1,19, round 2 x1,13 sur 10 fils et x1,05 sur un fil : une clé compacte sans perte rapporterait moins, pas assez pour le chantier pour l'instant |
| 2026-10-09 | Mac M4, chargé (charge 11 à 14) | bilan de la phase 4 à ce point : version d'avant (hachage dérivé, `Mutex`) contre l'actuelle, banc A/B en alternance | round 4 : 1,7 → 0,8 µs (x2,1) ; round 3 : 159 → 72 µs (x2,2) ; round 2 : 56,3 → 20,9 ms sur un fil (x2,7), 13,3 → 4,5 ms sur 10 fils (x3,0) ; partie entière : 16,5 → 5,2 s sous cette charge (x3,2), ~2,6 s quand la machine est calme |
| 2026-10-09 | Mac M4, chargé | première équivalence d'états : `last_round` oublié par la mémo quand aucune capacité du deck ne le lit ; décompte sur le banc, puis banc A/B | 14 decks sur 24 concernés ; pour eux, 116 139 → 53 193 états résolus depuis le round 2 (−54 %), 2 576 055 → 622 133 sur 3 parties entières (−76 %). Round 2 : 20,9 → 16,1 ms sur un fil (x1,30), 4,5 → 3,8 ms sur 10 fils (x1,18) ; partie entière 4,23 → 2,50 s (x1,69) ; round 3 inchangé (ses cartes jouées fixent déjà `last_round`) ; mêmes empreintes de valeurs |
| 2026-10-09 | Mac M4, chargé | équivalence affinée : ne garder du round précédent que ce que le deck lit (cartes pour After, vainqueur pour Revenge et Confidence) ; décompte sur les 10 decks du banc qui le lisent, puis banc A/B | 8 ne lisent que le vainqueur, 1 que les cartes, 1 les deux ; 70 229 → 55 049 états depuis le round 2 (−22 %), 1 846 802 → 732 575 sur 2 parties entières (−60 %). Round 2 x1,04 sur un fil, x1,13 sur 10 fils ; partie entière : 423 000 → 266 000 nœuds par main en moyenne, la plus lourde de 4,9-5,6 à 3,3 s, mémo 235 → 59 Mo ; moyenne dans le bruit ; mêmes empreintes |
