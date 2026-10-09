//! Des milliers de résolutions sous contrôle (étape 2.3) : chaque état de `search_states.jsonl` — 10 000 débuts du
//! round 3 de parties jouées au hasard, de jour comme de nuit, écrits par `scripts/build_search_states.py` — est résolu
//! jusqu'à la fin de la partie, sous les contrôles de la recherche : chaque matrice vérifiée par le solveur, chaque
//! valeur dans [0, 1], et chaque état résolu, vu de l'autre camp, vaut 1 − V. Un plantage ou un écart est rapporté
//! avec l'identifiant de l'état ; le round en cause devient alors un cas du corpus.
//!
//! Le contrôle [0, 1] est une assertion de debug : lancer ce test sans `--release`.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::panic::{self, AssertUnwindSafe};

use rayon::prelude::*;
use serde_json::Value;
use ur_engine::contract::{Deck, State};
use ur_engine::search::Search;

/// Un état de départ et son deck.
struct Start {
    id: String,
    deck: Deck,
    state: State,
}

fn start_states() -> Vec<Start> {
    let path = format!("{}/search_states.jsonl", corpus::CORPUS_DIR);
    let contents = std::fs::read_to_string(&path).unwrap_or_else(|_| {
        panic!("{path} introuvable : le générer avec scripts/build_search_states.py (depuis UrbanPy/Backend_fastAPI)")
    });
    contents
        .lines()
        .map(|line| {
            let fields: Value = serde_json::from_str(line).expect("ligne illisible");
            Start {
                id: fields["id"].as_str().expect("identifiant").to_string(),
                deck: corpus::parse_deck(&fields["deck"]).deck,
                state: corpus::parse_state(&fields["state"]),
            }
        })
        .collect()
}

#[test]
fn chaque_resolution_passe_les_controles() {
    let starts = start_states();
    assert!(!starts.is_empty());
    let alerts: Vec<String> = starts.par_iter().filter_map(alert).collect();
    assert!(
        alerts.is_empty(),
        "{} résolutions sur {} en alerte :\n{}",
        alerts.len(),
        starts.len(),
        alerts.join("\n")
    );
}

/// L'alerte de cette résolution, None si elle passe tous les contrôles.
fn alert(start: &Start) -> Option<String> {
    let resolution = panic::catch_unwind(AssertUnwindSafe(|| {
        let search = Search::new(&start.deck);
        search.value(&start.state);
        let mirror_deck = start.deck.mirrored();
        search.mirror_mismatches(&Search::new(&mirror_deck))
    }));
    match resolution {
        Ok(mismatches) if mismatches.is_empty() => None,
        Ok(mismatches) => Some(format!(
            "  {} : {} états, vus de l'autre camp, ne valent pas 1 − V ; le premier (état, V, miroir) : {:?}",
            start.id,
            mismatches.len(),
            mismatches[0]
        )),
        Err(panic) => {
            let message = panic
                .downcast_ref::<String>()
                .map(String::as_str)
                .or_else(|| panic.downcast_ref::<&str>().copied())
                .unwrap_or("?");
            Some(format!("  {} : plantage : {message}", start.id))
        }
    }
}
