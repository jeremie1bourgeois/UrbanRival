//! Moteur Urban Rivals compilé — la charpente.
//!
//! Le moteur Python (`UrbanPy/Backend_fastAPI/src/core/`) reste la référence : il résout un round en ~1 ms, ce qui
//! plafonne le solveur de l'IA (20 min pour une seule paire de mains à 12 pillz). L'objectif ici est ~10 µs, de quoi
//! résoudre des parties en masse. L'oracle de comparaison existe déjà : `src/core/engine/contract.py` fixe le format,
//! `scripts/build_engine_corpus.py` produit le corpus différentiel et `data/engine_digests.json` en garde l'empreinte.
//!
//! **Ce que cette charpente ne contient délibérément pas : la résolution d'un round.** Quatre points de règle sont
//! ouverts (`docs/REGLES.md` § Registre, R1 à R4) et portent précisément sur des ordres de résolution et des bornes :
//! l'ordre entre la carte alliée et la carte ennemie, le multiplicateur « Par Dégât » en défaite, le plancher du
//! « Par Vie / Pillz perdue », et la Protection face à un « Cards ». Les trancher changera le noyau de résolution et
//! obligera à régénérer le corpus. Le format de l'état et du deck, lui, n'en dépend pas : c'est ce qui est écrit ici.

pub mod contract;
pub mod vocabulary;
