//! Moteur Urban Rivals compilé.
//!
//! Le moteur Python (`UrbanPy/Backend_fastAPI/src/core/`) reste la référence ; celui-ci en est la transcription
//! rapide. `round::play` joue un round exactement comme `reference.play`, `game::legal_actions` et `game::terminal`
//! donnent les coups et la fin de partie de `reference.py` : `tests/differentiel.rs` et `tests/regles.rs` le
//! vérifient sur le corpus produit par `scripts/build_engine_corpus.py`, dont `data/engine_digests.json` garde
//! l'empreinte. `round::play_block` joue toutes les mises d'une paire de cartes, chaque case égale à `round::play`
//! (`tests/bloc.rs`). `nash::Solver` résout les matrices de la recherche, vérifié contre SciPy (`tests/nash.rs`).
//! Le cap : `docs/MOTEUR-RUST.md` ; l'état du travail : `UrbanRust/README.md`.
//!
//! Les règles encore ouvertes (`docs/REGLES.md`, registre) peuvent changer le moteur Python : on régénère alors le
//! corpus, et ce moteur suit.

pub mod contract;
pub mod game;
pub mod nash;
pub mod round;
pub mod vocabulary;
