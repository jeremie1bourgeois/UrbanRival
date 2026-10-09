# Moteur Rust — état du travail

À lire avant de toucher au code de ce dossier, et à mettre à jour à la fin de chaque étape. Le code vise la vitesse
avant la lisibilité : ce document dit ce qu'il fait et pourquoi il est écrit ainsi, pour qu'on puisse le reprendre
sans tout redécouvrir. Ce qu'on compte faire : [docs/PLAN-MOTEUR.md](../docs/PLAN-MOTEUR.md) ; le cap :
[docs/MOTEUR-RUST.md](../docs/MOTEUR-RUST.md).

## Où on en est

*Mis à jour le 2026-10-09 — plan : phase 1, étape 1.1 faite ; prochaine : 1.2 (résolution d'un round).*

Fait :
- le vocabulaire du contrat, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py` ; son empreinte est
  comparée à celle que Python écrit dans `data/engine_digests.json` ;
- l'état compact d'une partie (deck, état, coup, résultat) : types de taille fixe, copiables, sans tas ;
- le lecteur du corpus (étape 1.1) : les 8 familles (113 540 entrées, 29 365 decks) se relisent dans les types de
  `contract.rs` sans rien perdre. La preuve : réécrites depuis ces types en JSON canonique, elles redonnent
  exactement les empreintes de Python (un lecteur qui perd les effets persistants fait échouer 7 familles sur 8).

Pas encore fait : la résolution d'un round, et tout ce qui suit dans le plan.

Ce code a été écrit avant le plan. Il en respecte les règles de conception, mais rien n'y est figé : la disposition
de l'état peut changer si une mesure le justifie. Seuls les indices du vocabulaire sont intouchables, car ils sont
partagés avec Python.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `src/lib.rs` | point d'entrée de la crate |
| `src/vocabulary.rs` | vocabulaire figé : les indices partagés avec Python |
| `src/contract.rs` | état compact : deck, état, coup, résultat |
| `tests/vocabulaire.rs` | l'empreinte du vocabulaire égale celle de Python |
| `tests/corpus/mod.rs` | lecteur du corpus, partagé par les tests ; hors de la crate, car seuls les tests lisent du JSON |
| `tests/lecture_corpus.rs` | chaque famille relue puis réécrite redonne l'empreinte de Python |

## Lancer les tests

`./bootstrap.sh` (Windows : `bootstrap.ps1`) la première fois : installe rustup s'il manque, puis lance `cargo test`.
Ensuite, `cargo test`. La version du compilateur est fixée par `rust-toolchain.toml`.

Les tests lisent le corpus, qui n'est pas versionné : sur une copie neuve du dépôt, le générer d'abord avec
`scripts/build_engine_corpus.py` (depuis `UrbanPy/Backend_fastAPI`), sinon `tests/lecture_corpus.rs` échoue en le
disant. Le profil de test compile la crate en -O1 et ses dépendances en -O3 (`Cargo.toml`) : relire tout le corpus
passe ainsi de 35 s à 5 s.

## Comment le code est vérifié

- **Python est la référence.** Le corpus de non-régression se génère avec `scripts/build_engine_corpus.py` (depuis
  `UrbanPy/Backend_fastAPI`) ; il n'est pas versionné, ses empreintes le sont (`data/engine_digests.json`).
- **Chaque version optimisée garde une version plus simple comme référence de test** : moteur Python → round simple
  en Rust → bloc de mises. Un code illisible reste ainsi comparable, case par case, à un code qu'on peut relire.

## Optimisations en place

Chaque astuce qui rend le code moins lisible est inscrite ici : ce qu'elle fait, où, pourquoi, ce qu'elle a fait
gagner, et quel test garantit qu'elle ne change pas les résultats. Le code porte un commentaire court qui renvoie ici.

| Optimisation | Où | Pourquoi | Gain mesuré | Garantie par |
|---|---|---|---|---|
| État de taille fixe, copiable, sans tas ; cases d'effets vides normalisées | `src/contract.rs` | l'IA copie, hache et compare des états par millions ; deux chemins vers le même état doivent se hacher pareil | pas encore mesuré | tests de `contract.rs` |
| Capacités réduites à des indices et des masques de bits | `src/contract.rs`, `src/vocabulary.rs` | aucun texte manipulé pendant un round | pas encore mesuré | `tests/vocabulaire.rs` |

## Écarts connus et points ouverts

- Généré sous Windows, le corpus finit ses lignes par `\r\n`, alors que Python empreinte les lignes terminées par
  `\n` : hacher les fichiers tels quels ne redonne pas les empreintes. Le lecteur accepte les deux fins de ligne, et
  le test réécrit les lignes au lieu de hacher les fichiers.
- Les règles encore ouvertes (R1 surtout, un ordre de résolution ; [docs/REGLES.md](../docs/REGLES.md),
  registre) peuvent changer le moteur Python : on régénère alors le corpus, et le moteur Rust suit.
