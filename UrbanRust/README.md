# Moteur Rust — état du travail

À lire avant de toucher au code de ce dossier, et à mettre à jour à la fin de chaque étape. Le code vise la vitesse
avant la lisibilité : ce document dit ce qu'il fait et pourquoi il est écrit ainsi, pour qu'on puisse le reprendre
sans tout redécouvrir. Ce qu'on compte faire : [docs/PLAN-MOTEUR.md](../docs/PLAN-MOTEUR.md) ; le cap :
[docs/MOTEUR-RUST.md](../docs/MOTEUR-RUST.md).

## Où on en est

*Mis à jour le 2026-10-09 — plan : phase 1, étapes 1.1 à 1.6 faites ; prochaine : 1.7 (les équilibres d'une
matrice).*

Fait :
- le vocabulaire du contrat, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py` ; son empreinte est
  comparée à celle que Python écrit dans `data/engine_digests.json` ;
- l'état compact d'une partie (deck, état, coup, résultat) : types de taille fixe, copiables, sans tas ;
- le lecteur du corpus (étape 1.1) : les 8 familles (113 510 entrées, 29 365 decks) se relisent dans les types de
  `contract.rs` sans rien perdre. La preuve : réécrites depuis ces types en JSON canonique, elles redonnent
  exactement les empreintes de Python (un lecteur qui perd les effets persistants fait échouer 7 familles sur 8) ;
- la résolution d'un round (étape 1.2), `round::play` : les 8 familles du corpus sont identiques à 100 % au moteur
  Python, état suivant et issue du combat (113 510 rounds). C'est la version simple, transcrite fonction par fonction
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
  donne les deux stratégies d'un seul tableau, avec la règle de Bland pour ne jamais cycler. Chaque solution est
  vérifiée : écart à l'équilibre ≤ 1e-9 et valeur entre ce que garantissent les deux stratégies, sinon le solveur
  s'arrête net. Mêmes valeurs que SciPy sur 102 matrices aléatoires (plus grand écart 1,7e-15) ; l'exemple d'IA.md
  § 4.4 est un test. Tampons réutilisés : un solveur dimensionné n'alloue plus rien.

Pas encore fait : les équilibres d'une matrice (1.7), et tout ce qui suit dans le plan.

Ce code a été écrit avant le plan. Il en respecte les règles de conception, mais rien n'y est figé : la disposition
de l'état peut changer si une mesure le justifie. Seuls les indices du vocabulaire sont intouchables, car ils sont
partagés avec Python.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `src/lib.rs` | point d'entrée de la crate |
| `src/vocabulary.rs` | vocabulaire figé : les indices partagés avec Python |
| `src/contract.rs` | état compact : deck, état, coup, résultat |
| `src/game.rs` | coups légaux et fin de partie (`reference.py`) |
| `src/nash.rs` | solveur de jeux matriciels à somme nulle : point-selle, sinon simplexe ; chaque solution vérifiée |
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
| `tests/nash.rs` | le solveur donne la valeur de SciPy sur les matrices de `data/nash_expected.json` |
| `tests/sans_allocation.rs` | aucune allocation pendant un round, un bloc, les coups légaux, la fin de partie, et pour un solveur déjà dimensionné |

## Lancer les tests

`./bootstrap.sh` (Windows : `bootstrap.ps1`) la première fois : installe rustup s'il manque, puis lance `cargo test`.
Ensuite, `cargo test`. La version du compilateur est fixée par `rust-toolchain.toml`.

Les tests lisent le corpus, qui n'est pas versionné : sur une copie neuve du dépôt, le générer d'abord avec
`scripts/build_engine_corpus.py` (depuis `UrbanPy/Backend_fastAPI`), sinon `tests/lecture_corpus.rs` échoue en le
disant. Le profil de test compile la crate en -O1 et ses dépendances en -O3 (`Cargo.toml`) : relire tout le corpus
passe ainsi de 35 s à 5 s. Le plus long est `tests/bloc.rs` (~11 s sur un i7-8750H, réparti sur les cœurs) : il
rejoue ~29 millions de cases deux fois, en bloc et en round simple.

## Comment le code est vérifié

- **Python est la référence.** Le corpus de non-régression se génère avec `scripts/build_engine_corpus.py` (depuis
  `UrbanPy/Backend_fastAPI`) : les rounds joués de chaque famille, plus `regles.jsonl` pour les coups légaux et la
  fin de partie. Il n'est pas versionné, ses empreintes le sont (`data/engine_digests.json`).
- **SciPy est la référence du solveur** : `scripts/build_nash_expected.py` (SciPy, dans `requirements-dev.txt`) écrit
  `data/nash_expected.json`, versionné ; une matrice peut avoir plusieurs équilibres, les tests comparent la valeur.
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

- Le solveur coûte cher sur les grandes matrices aléatoires : ~320 µs pour une 23 × 92, presque autant que les ~2 100
  cases de moteur qui la remplissent. La règle de Bland, sûre mais lente en nombre de pivots, en est la cause probable ;
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
