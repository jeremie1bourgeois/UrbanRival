# Moteur Rust et solveur Nash — lignes directrices

Ce document donne le cap : ce qu'on cherche à atteindre et les principes qui guident la construction du moteur
rapide. Le déroulé concret est dans le [plan d'exécution](PLAN-MOTEUR.md) ; le pourquoi de l'IA dans [IA.md](IA.md).

## Objectif

**Calculer le plus de branches et de nœuds possible, en le moins de temps possible.** Plus le moteur va vite, plus
on remonte loin en Nash exact, et moins on dépend du modèle.

| Palier | Nash exact sur | Ce que ça donne |
|---|---|---|
| Premier | les rounds 3 et 4 | des datasets sur deux rounds |
| **Visé** | les rounds 2, 3 et 4 | des datasets sur trois rounds ; le modèle ne sert qu'à la décision du round 1 (Nash sur le round 1, avec la valeur que le modèle donne aux états de début de round 2) ; dès le round 2, Nash exact jusqu'à la fin, sans modèle |
| Idéal | la partie entière | une paire de mains résolue de bout en bout, sans modèle |

Résoudre la partie entière **pour une paire de mains** n'est pas forcément hors de portée : nos extrapolations donnent
quelques centaines de millions de branches, peut-être davantage, à confirmer par la mesure. Ce qui reste impossible,
c'est de le faire pour toutes les paires de mains possibles : c'est pour ça qu'il faut un modèle qui généralise.

Les datasets se calculent **sans élagage** : chaque valeur est exacte. Et chaque exemple garde **tous les équilibres
de Nash** de sa décision, pas un seul : une position n'a qu'une valeur, mais souvent plusieurs façons optimales de
jouer, et le modèle doit pouvoir être entraîné sur celle qui est la plus proche de sa prédiction.

## Lignes directrices

1. **Le moteur Python est la référence.** À état et coups identiques, le moteur Rust donne exactement le même
   résultat ; toute optimisation se vérifie contre lui.
2. **Tout le calcul intensif est en Rust.** Python (FastAPI, entraînement) n'appelle Rust qu'une fois par coup ou
   par lot, jamais à chaque round simulé.
3. **La vitesse vient de la conception plus que du langage.** États compacts, aucune allocation pendant un round,
   capacités réduites à des nombres. Ce qui ne dépend que des cartes jouées se calcule une fois, pas pour chaque
   combinaison de mises. Un état déjà résolu ne se résout pas deux fois.
4. **Les matrices de Nash sont petites** (au plus 23 × 92) **et se résolvent sur CPU**, avec un solveur écrit pour
   elles : solution pure d'abord, sinon simplexe. Chaque solution est vérifiée. Les bibliothèques généralistes
   (HiGHS, SciPy) servent seulement à tester.
5. **Le parallélisme se fait entre états indépendants**, sur tous les cœurs, pas à l'intérieur d'une matrice.
6. **Le GPU sert au réseau** (entraînement, évaluation des positions), pas au moteur ni aux matrices.
7. **On mesure avant d'optimiser.** Chaque accélération est mesurée avant et après, sur le même banc d'essai.

## Outils

| Pour | Outil |
|---|---|
| Moteur, solveur, recherche | Rust ; `rayon` pour répartir sur les cœurs |
| Liaison avec Python | `pyo3` + `maturin` |
| Réseau | entraînement PyTorch ; inférence depuis Rust par ONNX Runtime (`ort`) |
| Mesure | `criterion` (benchmarks), `samply` (profilage) |
| Machines | Mac M4 pour développer ; serveurs CPU multicœurs pour les datasets ; GPU NVIDIA (Modal) pour le réseau |

## Ce qu'on écarte

- **Résoudre les matrices sur GPU** : trop petites pour en tirer profit, et les méthodes GPU donnent des solutions
  approchées. À revoir seulement si les matrices deviennent le poste dominant une fois le reste optimisé.
- **Un solveur généraliste dans la boucle** : sur des matrices aussi petites, son coût fixe par appel dépasse le
  calcul lui-même.
- **Python dans la boucle**, et **une réécriture en C ou C++** : rien à y gagner.

*Établi le 2026-10-08.*
