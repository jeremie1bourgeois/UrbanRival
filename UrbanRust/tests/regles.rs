//! Les coups légaux et la fin de partie du moteur Rust sont-ils exactement ceux de `reference.py` ?
//!
//! `regles.jsonl` (écrit par `corpus.rules_summary`) donne, pour des états qui parcourent tout le domaine des deux
//! fonctions, les coups de chaque camp dans l'ordre de Python et la valeur de fin de partie. Que le fichier soit
//! celui qu'épingle `data/engine_digests.json`, `tests/lecture_corpus.rs` le vérifie.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use ur_engine::contract::Action;
use ur_engine::game::{legal_actions, terminal};

#[test]
fn coups_legaux_et_fin_de_partie_identiques_a_python() {
    let entries = corpus::read_rules();
    let divergent: Vec<String> = entries
        .iter()
        .filter_map(|entry| {
            let ally: Vec<Action> = legal_actions(&entry.state.ally).collect();
            let enemy: Vec<Action> = legal_actions(&entry.state.enemy).collect();
            let value = terminal(&entry.state);
            let identical = ally == entry.ally_actions && enemy == entry.enemy_actions && value == entry.terminal;
            (!identical).then(|| {
                format!(
                    "  {:?}\n    attendu {:?} / {} / {} coups\n    obtenu  {value:?} / {} / {} coups",
                    entry.state,
                    entry.terminal,
                    entry.ally_actions.len(),
                    entry.enemy_actions.len(),
                    ally.len(),
                    enemy.len()
                )
            })
        })
        .collect();
    assert!(
        divergent.is_empty(),
        "{} états sur {} divergent de Python :\n{}",
        divergent.len(),
        entries.len(),
        divergent[..divergent.len().min(5)].join("\n")
    );
}
