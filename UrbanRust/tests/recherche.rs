//! La recherche exacte donne-t-elle les valeurs du solveur Python de référence ?
//!
//! `data/search_expected.json` (écrit par `scripts/build_search_expected.py`, lentement, avec `reference.step` et
//! SciPy) : des états de rounds 4 et 3, leur deck, leur valeur pour l'allié et la valeur de chaque carte du premier
//! joueur pour lui. On compare aussi le nombre d'états distincts résolus : il ne coïncide que si les deux moteurs
//! identifient les états de la même façon et atteignent les mêmes. Le mode parallèle doit donner les mêmes nombres
//! que le mode à un seul fil, au bit près.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::collections::HashSet;

use serde_json::Value;
use ur_engine::contract::{Deck, State};
use ur_engine::game::terminal;
use ur_engine::search::Search;

/// La récursion empile des résolutions de matrices, chacune à ~1e-12 près.
const AGREEMENT: f64 = 1e-9;
/// États du round 2 de la famille `aleatoire` sur lesquels comparer les deux modes.
const ROUND_2_STATES: usize = 4;

/// Un état de `data/search_expected.json` et ce qu'en dit le solveur Python.
struct Expected {
    name: String,
    deck: Deck,
    state: State,
    value: f64,
    card_values: Vec<Option<f64>>,
    states: usize,
}

fn expected_states() -> Vec<Expected> {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/search_expected.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/search_expected.json introuvable");
    let expected: Value = serde_json::from_str(&contents).expect("data/search_expected.json illisible");
    let entries: Vec<Expected> = expected
        .as_array()
        .expect("liste d'états attendue")
        .iter()
        .map(|entry| Expected {
            name: entry["name"].as_str().unwrap().to_string(),
            deck: corpus::parse_deck(&entry["deck"]).deck,
            state: corpus::parse_state(&entry["state"]),
            value: entry["value"].as_f64().unwrap(),
            card_values: entry["card_values"]
                .as_array()
                .unwrap()
                .iter()
                .map(Value::as_f64)
                .collect(),
            states: entry["states"].as_u64().unwrap() as usize,
        })
        .collect();
    assert!(!entries.is_empty());
    entries
}

#[test]
fn chaque_etat_a_la_valeur_du_solveur_python() {
    let entries = expected_states();
    let mut divergent = Vec::new();
    for expected in &entries {
        let search = Search::new(&expected.deck);
        let card_values = search.card_values(&expected.state);
        let best = card_values
            .iter()
            .flatten()
            .fold(f64::NEG_INFINITY, |best, value| best.max(*value));
        let value = if expected.state.ally_first { best } else { 1.0 - best };
        let states = search.solved_states() + 1; // l'état de départ, résolu sans passer par la mémo

        let cards_agree =
            card_values
                .iter()
                .zip(&expected.card_values)
                .all(|(found, expected)| match (found, expected) {
                    (Some(found), Some(expected)) => (found - expected).abs() <= AGREEMENT,
                    (None, None) => true,
                    _ => false,
                });
        if !cards_agree || (value - expected.value).abs() > AGREEMENT || states != expected.states {
            divergent.push(format!(
                "  {} : valeur {value} contre {}, cartes {card_values:?} contre {:?}, {states} états contre {}",
                expected.name, expected.value, expected.card_values, expected.states
            ));
        }
    }
    assert!(
        divergent.is_empty(),
        "{} états sur {} divergent du solveur Python :\n{}",
        divergent.len(),
        entries.len(),
        divergent.join("\n")
    );
}

#[test]
fn le_mode_parallele_donne_les_memes_valeurs_qu_un_seul_fil() {
    let mut roots: Vec<(Deck, State)> = expected_states()
        .into_iter()
        .map(|expected| (expected.deck, expected.state))
        .collect();
    let family = corpus::read_family("aleatoire");
    let mut seen = HashSet::new();
    let round_2: Vec<(Deck, State)> = family
        .entries
        .iter()
        .filter(|entry| entry.state.nb_turn == 2 && terminal(&entry.state).is_none())
        .filter(|entry| seen.insert((entry.deck, entry.state)))
        .map(|entry| (family.decks[entry.deck].deck, entry.state))
        .collect();
    roots.extend(
        round_2
            .iter()
            .step_by(round_2.len() / ROUND_2_STATES)
            .take(ROUND_2_STATES)
            .copied(),
    );

    for (deck, state) in &roots {
        let (single, parallel) = (Search::new(deck), Search::parallel(deck));
        assert_eq!(single.card_values(state), parallel.card_values(state), "{state:?}");
        assert_eq!(single.solved_states(), parallel.solved_states(), "{state:?}");
    }
}
