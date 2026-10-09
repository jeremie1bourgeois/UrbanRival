# Moteur Rust — état du travail

À lire avant de toucher au code de ce dossier, et à mettre à jour à la fin de chaque étape. Le code vise la vitesse
avant la lisibilité : ce document dit ce qu'il fait et pourquoi il est écrit ainsi, pour qu'on puisse le reprendre
sans tout redécouvrir. Ce qu'on compte faire : [docs/PLAN-MOTEUR.md](../docs/PLAN-MOTEUR.md) ; le cap :
[docs/MOTEUR-RUST.md](../docs/MOTEUR-RUST.md).

## Où on en est

*Mis à jour le 2026-10-09 — plan : phases 1 et 2 faites (étapes 1.1 à 1.11, 2.1 à 2.3) ; prochaine : phase 3, 3.1
(banc d'essai fixe).*

Fait :
- le vocabulaire du contrat, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py` ; son empreinte est
  comparée à celle que Python écrit dans `data/engine_digests.json` ;
- l'état compact d'une partie (deck, état, coup, résultat) : types de taille fixe, copiables, sans tas ;
- le lecteur du corpus (étape 1.1) : les 8 familles (113 510 entrées, 29 365 decks) se relisent dans les types de
  `contract.rs` sans rien perdre. La preuve : réécrites depuis ces types en JSON canonique, elles redonnent
  exactement les empreintes de Python (un lecteur qui perd les effets persistants fait échouer 7 familles sur 8) ;
- la résolution d'un round (étape 1.2), `round::play` : les 9 familles du corpus sont identiques à 100 % au moteur
  Python, état suivant et issue du combat (113 949 rounds), dont `reels` : les 439 rounds de 115 combats réels
  capturés du client officiel (`data/ur_battles`, rejoués avec les choix réellement faits ; les 4 autres combats
  portent un pouvoir exclu). Le Python reproduisant ces combats (`tests/test_ur_battles.py`), le Rust les reproduit
  aussi. C'est la version simple, transcrite fonction par fonction
  de `process_round.py` et des quatre niveaux de capacités : la référence lisible contre laquelle se vérifieront les
  versions rapides. Mesure informelle en release : ~2,8 millions de rounds/s sur un cœur (i7-8750H) ;
- les coups légaux et la fin de partie (étape 1.3), `game::legal_actions` et `game::terminal` : identiques à
  `reference.py` sur les 1 536 états de `regles.jsonl` (chaque main jouée × chaque stock de pillz de 0 à 15, chaque
  round × chaque paire de vies de 0 à 15), coups dans le même ordre. `legal_actions` est un itérateur : rien n'est
  alloué ;
- le bloc de mises (étape 1.4), `round::play_block` : toutes les combinaisons de mises d'une paire de cartes, chaque
  case identique au round simple sur les 88 132 blocs distincts du corpus (~29 millions de cases). Le premier étage
  du round se calcule une fois par tranche de mises ; gain x2,3 par case (voir « Optimisations en place ») ;
- aucune allocation (étape 1.5) : un round, un bloc de mises, les coups légaux et la fin de partie n'allouent rien,
  en debug comme en release. `tests/sans_allocation.rs` installe un allocateur qui compte les allocations du fil
  courant ; il vérifie d'abord que le compteur voit une allocation, pour ne pas passer à vide ;
- le solveur de matrices (étape 1.6), `nash::Solver` : la valeur et un équilibre d'un jeu à somme nulle (lignes =
  le joueur qui maximise). Un point-selle d'abord, en O(n·m) ; sinon le simplexe sur le jeu décalé (valeurs ≥ 1), qui
  donne les deux stratégies d'un seul tableau : entre la première variable de coût réduit négatif, les égalités du
  rapport se départagent lexicographiquement (ni cycle, ni base dégénérée du problème perturbé). Chaque solution est
  vérifiée : écart à l'équilibre ≤ 1e-9 et valeur entre ce que garantissent les deux stratégies, sinon le solveur
  s'arrête net. Mêmes valeurs que SciPy sur 102 matrices aléatoires (plus grand écart 1,7e-15) ; l'exemple d'IA.md
  § 4.4 est un test. Tampons réutilisés : un solveur dimensionné n'alloue plus rien ;
- les équilibres d'une matrice (étape 1.7), `Solver::equilibria` : pour chaque coup de chaque joueur, la stratégie
  optimale qui le joue avec la plus forte probabilité (0 : le coup n'est joué dans aucun équilibre). Les équilibres
  d'un jeu à somme nulle forment un produit (toute stratégie optimale des lignes avec toute stratégie optimale des
  colonnes) ; avec sa valeur, la matrice décrit exactement leur ensemble, {p ≥ 0, Σ p = 1, pᵀ M ≥ valeur} : c'est
  elle que les datasets garderont. On repart du tableau optimal, les variables de coût réduit strictement positif
  interdites (elles sont nulles dans toute stratégie optimale), pour maximiser la variable du coup ; les lignes
  passent par le même calcul sur −Mᵀ. Chaque stratégie rendue est vérifiée ; la plus forte probabilité de chacun des
  1 974 coups des matrices de SciPy est celle que donne SciPy (plus grand écart 5,5e-12) ;
- tous les coins (étape 1.8), `Solver::corners` : les sommets de l'ensemble des stratégies optimales de chaque joueur
  (toute stratégie optimale en est un mélange), au plus 256 par joueur, la troncature signalée. On visite, de proche
  en proche depuis la base trouvée, les bases de la face optimale ; grâce au départage lexicographique, ce sont les
  sommets d'un polytope perturbé non dégénéré, dont le graphe est connexe et dont chaque coin réel est l'image.
  Chaque base est recalculée depuis le tableau initial, chaque coin vérifié. Mêmes coins que la force brute de SciPy
  sur 72 matrices (144 listes) ; sur les 102, le maximum de chaque coordonnée sur les coins redonne la plus forte
  probabilité du coup. Sur les matrices réelles du round 4 : toutes à point-selle, et pourtant jusqu'à 19 coins par
  joueur (`aleatoire`), aucune liste tronquée.

- les valeurs attendues de la recherche (étape 1.9, côté Python) : `data/search_expected.json`, la valeur exacte de
  68 états de rounds 4 et 3 selon le solveur Python de référence (voir « Comment le code est vérifié »).

- la recherche exacte avec mémo (étape 1.10), `search::Search` : V(état) selon `docs/IA.md` § 5.1, les matrices
  remplies par blocs de mises (transposés quand le premier joueur est l'ennemi) et résolues par `nash::Solver`.
  Mêmes valeurs que le solveur Python de référence sur ses 68 états (valeur, valeur de chaque carte, nombre d'états
  distincts résolus), en 0,13 s contre ~17 min. Un seul fil : round 3 en 4 ms en moyenne, round 2 en 0,14 s en
  moyenne et 2,5 s au plus (états les plus riches en pillz, ~43 000 états résolus), contre ~4 h extrapolées en Python.

- le parallélisme (étape 1.11), `Search::parallel` : les états suivants des rounds 1 à 3 répartis sur les cœurs par
  rayon, une mémo partagée en 64 morceaux sous verrou, un solveur par fil. La valeur d'un état se calcule de la même
  façon quel que soit le fil : mêmes nombres au bit près qu'en un seul fil (`tests/recherche.rs`, dont des états du
  round 2). Sur 6 cœurs : x4,3 à x4,5 sur un état du round 2 ; x4,4 sur des états indépendants, chacun sa recherche.

- le corpus élargi (étape 2.1) : une dixième famille, `masse`, 2 000 parties jouées au hasard avec les mains de
  `hands.py`, de nuit une fois sur deux (les cartes prennent alors leurs textes « Night: ») : 37 665 rounds, 82 % des
  niveaux de cartes tirables, 22 des 30 textes de nuit. Le Rust y est identique au Python du premier coup, rounds et
  blocs de mises : le corpus compte désormais 151 614 rounds et 112 945 blocs distincts (~35 millions de cases).
  `aleatoire` (300 parties, de jour) reste le petit échantillon de mains réalistes dont se servent les tests.

- les contrôles pendant la recherche (étape 2.2) : chaque matrice est vérifiée par le solveur, toujours (écart à
  l'équilibre, étape 1.6) ; en mode test (assertions de debug, actives sous `cargo test`, absentes en release),
  chaque valeur est une probabilité, dans [0, 1] ; `Search::mirror_mismatches` revoit chaque état résolu de l'autre
  camp (`State::mirrored`, sur `Deck::mirrored`) et rend ceux qui ne valent pas 1 − V. Il compare des valeurs, pas
  des ensembles d'états : l'asymétrie connue du round (`KNOWN_ASYMMETRIES`, l'ordre d'enregistrement des effets
  persistants) mène parfois le miroir à un état aux mêmes effets dans un autre ordre (14 états sur 501 157 contrôlés
  depuis 2 011 états de départ), sans en changer la valeur : aucun écart. `tests/recherche.rs` contrôle ainsi ses
  72 états de départ, et vérifie d'abord que le contrôle voit un faux miroir (le deck non échangé).

- les résolutions en masse (étape 2.3) : `tests/resolutions.rs` résout 10 000 débuts du round 3 de parties jouées
  au hasard, de jour comme de nuit (`scripts/build_search_states.py`), sous ces contrôles : aucune alerte ni
  plantage. ~4 s en profil de test sur 6 cœurs, contrôle miroir compris (640 154 états résolus, au plus 1 076 pour
  une résolution ; 376 valeurs fractionnaires). Le premier passage a levé 4 alertes : deux règles du moteur Python
  dépendaient du camp, et le Rust les reproduisait fidèlement. Un double KO déclarait l'allié perdant ; au niveau 3,
  deux pertes sur un même joueur s'appliquaient dans l'ordre des camps. Tranchées par décision (match nul ; le
  plancher le plus haut d'abord, comme au niveau 2), corrigées dans les deux moteurs avec leurs tests de bout en
  bout ; le corpus en porte des cas (`regles.jsonl` pour le double KO, `oculus` et `masse` pour l'ordre des pertes).

Pas encore fait : la phase 3 (mesurer), et tout ce qui suit dans le plan.

Ce code a été écrit avant le plan. Il en respecte les règles de conception, mais rien n'y est figé : la disposition
de l'état peut changer si une mesure le justifie. Seuls les indices du vocabulaire sont intouchables, car ils sont
partagés avec Python.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `src/lib.rs` | point d'entrée de la crate |
| `src/vocabulary.rs` | vocabulaire figé : les indices partagés avec Python |
| `src/contract.rs` | état compact : deck, état, coup, résultat ; la même partie vue de l'autre camp (`mirrored`) |
| `src/game.rs` | coups légaux et fin de partie (`reference.py`) |
| `src/search.rs` | recherche exacte avec mémo : V(état), les matrices remplies par blocs de mises ; sur un fil ou sur tous les cœurs ; les contrôles : valeurs dans [0, 1], 1 − V vu de l'autre camp |
| `src/nash.rs` | solveur de jeux matriciels à somme nulle : point-selle, sinon simplexe ; chaque solution vérifiée ; pour chaque coup, l'équilibre qui le joue le plus ; tous les coins des équilibres |
| `src/round/mod.rs` | un round (`process_round.py`) : mises, conditions de début de round, Leader, combat, ordre des niveaux ; en deux étages, avant et après les mises |
| `src/round/block.rs` | le bloc de mises : toutes les combinaisons de mises d'une paire de cartes, premier étage partagé |
| `src/round/clan.rs` | clan d'une carte en main, bonus de clan, Oculus infiltré (`clan.py`) |
| `src/round/multipliers.rs` | multiplicateurs des capacités, champ `how` (`multipliers.py`) |
| `src/round/level1.rs` … `level4.rs` | les quatre niveaux de capacités (`apply_capacity_lvl_1.py` … `_4.py`) |
| `tests/vocabulaire.rs` | l'empreinte du vocabulaire égale celle de Python |
| `tests/corpus/mod.rs` | lecteur du corpus, partagé par les tests ; hors de la crate, car seuls les tests lisent du JSON |
| `tests/lecture_corpus.rs` | chaque famille, et `regles.jsonl`, relus puis réécrits redonnent l'empreinte de Python |
| `tests/differentiel.rs` | chaque round du corpus, rejoué en Rust, redonne l'état suivant et l'issue de Python |
| `tests/regles.rs` | coups légaux et fin de partie identiques à ceux de Python, sur `regles.jsonl` |
| `tests/bloc.rs` | chaque case de chaque bloc du corpus égale le round simple, dans l'ordre des coups légaux |
| `tests/recherche.rs` | la recherche donne les valeurs du solveur Python de référence (`data/search_expected.json`) ; le mode parallèle, celles d'un seul fil ; vu de l'autre camp, chaque état résolu vaut 1 − V |
| `tests/nash.rs` | le solveur donne la valeur de SciPy, la plus forte probabilité de chaque coup et les coins de la force brute, sur les matrices de `data/nash_expected.json` |
| `tests/resolutions.rs` | 10 000 résolutions depuis le round 3, sur des mains au hasard, sans alerte des contrôles ni plantage |
| `tests/sans_allocation.rs` | aucune allocation pendant un round, un bloc, les coups légaux, la fin de partie, et pour un solveur déjà dimensionné (valeur et équilibres) |

## Lancer les tests

`./bootstrap.sh` (Windows : `bootstrap.ps1`) la première fois : installe rustup s'il manque, puis lance `cargo test`.
Ensuite, `cargo test`. La version du compilateur est fixée par `rust-toolchain.toml`.

Les tests lisent le corpus, qui n'est pas versionné : sur une copie neuve du dépôt, le générer d'abord avec
`scripts/build_engine_corpus.py` (depuis `UrbanPy/Backend_fastAPI`), sinon `tests/lecture_corpus.rs` échoue en le
disant ; de même, les états de départ de `tests/resolutions.rs` avec `scripts/build_search_states.py` (~75 s). Le profil de test compile la crate en -O1 et ses dépendances en -O3 (`Cargo.toml`) : relire tout le corpus
passe ainsi de 35 s à 5 s. Le plus long est `tests/bloc.rs` (~18 s sur un i7-8750H, réparti sur les cœurs) : il
rejoue ~35 millions de cases deux fois, en bloc et en round simple.

## Comment le code est vérifié

- **Python est la référence.** Le corpus de non-régression se génère avec `scripts/build_engine_corpus.py` (depuis
  `UrbanPy/Backend_fastAPI`) : les rounds joués de chaque famille, plus `regles.jsonl` pour les coups légaux et la
  fin de partie. Il n'est pas versionné, ses empreintes le sont (`data/engine_digests.json`).
- **SciPy est la référence du solveur** : `scripts/build_nash_expected.py` (SciPy, dans `requirements-dev.txt`) écrit
  `data/nash_expected.json`, versionné ; une matrice peut avoir plusieurs équilibres, les tests comparent des nombres
  uniques : la valeur, la plus forte probabilité de chaque coup dans un équilibre, et l'ensemble des coins.
- **Le solveur Python de référence est la référence de la recherche** : `scripts/build_search_expected.py` applique
  lentement la récursion de `docs/IA.md` § 5.1 (`reference.step`, SciPy pour chaque matrice, mémo par état) et écrit
  `data/search_expected.json`, versionné : pour 68 états de rounds 4 et 3, le deck, l'état, la valeur pour l'allié, la
  valeur de chaque carte du premier joueur et le nombre d'états distincts résolus. Les états viennent de parties
  aléatoires (graine fixe) ; leurs mains sont souvent si inégales que la valeur vaut 0, ½ ou 1, d'où l'ajout des
  états du round 3 les plus riches en pillz et de « jumeaux » (la même main des deux côtés, mêmes vies et pillz), où
  le bluff donne des valeurs fractionnaires (4/7, 1/3). ~17 min à régénérer.
- **Aucune carte au pouvoir non géré.** Le Python remplace un pouvoir que son parseur ne gère pas par « pas de
  pouvoir », sans le signaler : Rust et Python joueraient la carte faux, à l'identique. `compile_card`
  (`src/core/engine/contract.py`) refuse donc une telle carte (`ValueError`), et les mains aléatoires
  (`src/core/engine/hands.py`) ne tirent que les niveaux dont l'ability et le bonus sont gérés ;
  `tests/test_engine_contract.py` et `tests/test_engine_hands.py` le vérifient.
- **Chaque version optimisée garde une version plus simple comme référence de test** : moteur Python → round simple
  en Rust → bloc de mises. Un code illisible reste ainsi comparable, case par case, à un code qu'on peut relire.
- **Aucune allocation dans le chemin chaud** : `tests/sans_allocation.rs` le vérifie ; une optimisation qui en
  ajouterait une le fait échouer.

## Optimisations en place

Chaque astuce qui rend le code moins lisible est inscrite ici : ce qu'elle fait, où, pourquoi, ce qu'elle a fait
gagner, et quel test garantit qu'elle ne change pas les résultats. Le code porte un commentaire court qui renvoie ici.

| Optimisation | Où | Pourquoi | Gain mesuré | Garantie par |
|---|---|---|---|---|
| État de taille fixe, copiable, sans tas ; cases d'effets vides normalisées | `src/contract.rs` | l'IA copie, hache et compare des états par millions ; deux chemins vers le même état doivent se hacher pareil | pas encore mesuré | tests de `contract.rs` |
| Capacités réduites à des indices et des masques de bits | `src/contract.rs`, `src/vocabulary.rs` | aucun texte manipulé pendant un round | pas encore mesuré | `tests/vocabulaire.rs` |
| Bloc de mises : le premier étage du round (clans, Leader, conditions, copies, niveau 1, puissance et dégâts) calculé une fois par tranche de mises, puis copié pour chaque case ; une tranche = les mises de même signature pour les conditions Bet du deck | `src/round/block.rs`, coupure `first_stage` / `second_stage` dans `src/round/mod.rs` | le premier étage pèse ~60 % d'un round et ne lit la mise que par les conditions Bet (les multiplicateurs « Par Pillz » lisent le stock d'avant la mise) | x2,3 par case (release, i7-8750H : 448 → 198 ns sur tout le corpus) | `tests/bloc.rs` ; une signature qui ignore les Bet y fait diverger 1 419 blocs |

## Écarts connus et points ouverts

- La recherche est écrite simplement, en attendant le profil de la phase 3 : mémo en 64 `HashMap` sous verrou, au
  hachage standard (SipHash, calculé une fois pour choisir le morceau, une fois dans la table), une matrice et une
  liste d'états suivants allouées à chaque état résolu. Sur un fil, elle paraît ~20 % plus lente que la version sans
  verrou de l'étape 1.10 : à confirmer sur le banc.
- `rayon` est la seule dépendance du moteur, et seule la recherche s'en sert : le round n'en a aucune.

- `Solver::corners` alloue (listes de coins de taille variable, bases visitées) : c'est le chemin des datasets, une
  fois par décision, pas celui de la recherche ; `solve` et `equilibria` n'allouent rien.

- Le solveur coûte cher sur les grandes matrices aléatoires : ~320 µs pour une 23 × 92, presque autant que les ~2 100
  cases de moteur qui la remplissent. La règle d'entrée (la première variable de coût réduit négatif), sûre mais
  lente en nombre de pivots, en est la cause probable ;
  les parades (autre règle de pivot, lignes et colonnes dominées) sont des pistes de la phase 4, à confirmer sur des
  matrices réelles, peut-être plus souvent pures que les matrices aléatoires.

- Les pouvoirs exclus par décision ([docs/REGLES.md](../docs/REGLES.md), « Pouvoirs exclus » : Beyond, Rebirth,
  Hazard, Bypass, Illusion, Overdose, Remove Ability Conditions, le malus de Bugamon 2★) n'existent pas pour ce
  moteur : le parseur Python les rejette, ils n'atteignent ni le vocabulaire, ni le corpus, ni le code Rust, et rien
  ne doit être prévu pour eux.

- La carte compilée Rust porte `character` (indice dans la main du premier exemplaire de la carte) au lieu du nom
  que porte le contrat Python : le moteur lit l'identité d'une carte (le bonus de clan compte les personnages
  distincts, chaque Leader est son propre clan pour un Oculus), jamais son texte. Le lecteur du corpus le calcule
  depuis les noms ; une liaison Python devra faire de même.
- Le round panique là où le Python lève une erreur (`how` sans multiplicateur, condition de fin de round inattendue) :
  ces cas n'existent pas dans les cartes, le corpus le vérifie.

- Généré sous Windows, le corpus finit ses lignes par `\r\n`, alors que Python empreinte les lignes terminées par
  `\n` : hacher les fichiers tels quels ne redonne pas les empreintes. Le lecteur accepte les deux fins de ligne, et
  le test réécrit les lignes au lieu de hacher les fichiers.
- Les règles encore ouvertes (R1 surtout, un ordre de résolution ; [docs/REGLES.md](../docs/REGLES.md),
  registre) peuvent changer le moteur Python : on régénère alors le corpus, et le moteur Rust suit.
- Les 30 textes « Night: » n'entrent dans aucune famille construite : `solo` et `interactions` ne lisent que les
  textes de jour (`all_capacity_descriptions`). Seuls `masse` (22 sur 30) et les combats réels joués de nuit les
  exercent.
