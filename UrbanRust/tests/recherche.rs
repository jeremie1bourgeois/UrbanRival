//! La recherche exacte donne-t-elle les valeurs du solveur Python de référence ?
//!
//! `data/search_expected.json` (écrit par `scripts/build_search_expected.py`, lentement, avec `reference.step` et
//! SciPy) : des états de rounds 4 et 3, leur deck, leur valeur pour l'allié et la valeur de chaque carte du premier
//! joueur pour lui. On compare aussi le nombre d'états distincts résolus : il ne coïncide que si les deux moteurs
//! identifient les états de la même façon et atteignent les mêmes.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use serde_json::Value;
use ur_engine::search::Search;

/// La récursion empile des résolutions de matrices, chacune à ~1e-12 près.
const AGREEMENT: f64 = 1e-9;

#[test]
fn chaque_etat_a_la_valeur_du_solveur_python() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/search_expected.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/search_expected.json introuvable");
    let expected: Value = serde_json::from_str(&contents).expect("data/search_expected.json illisible");
    let entries = expected.as_array().expect("liste d'états attendue");
    assert!(!entries.is_empty());

    let mut divergent = Vec::new();
    for entry in entries {
        let name = entry["name"].as_str().unwrap();
        let deck = corpus::parse_deck(&entry["deck"]).deck;
        let state = corpus::parse_state(&entry["state"]);
        let mut search = Search::new(&deck);

        let card_values = search.card_values(&state);
        let expected_cards: Vec<Option<f64>> = entry["card_values"]
            .as_array()
            .unwrap()
            .iter()
            .map(Value::as_f64)
            .collect();
        let best = card_values
            .iter()
            .flatten()
            .fold(f64::NEG_INFINITY, |best, value| best.max(*value));
        let value = if state.ally_first { best } else { 1.0 - best };
        let expected_value = entry["value"].as_f64().unwrap();
        let states = search.solved_states() + 1; // l'état de départ, résolu sans passer par la mémo
        let expected_states = entry["states"].as_u64().unwrap() as usize;

        let cards_agree = card_values
            .iter()
            .zip(&expected_cards)
            .all(|(found, expected)| match (found, expected) {
                (Some(found), Some(expected)) => (found - expected).abs() <= AGREEMENT,
                (None, None) => true,
                _ => false,
            });
        if !cards_agree || (value - expected_value).abs() > AGREEMENT || states != expected_states {
            divergent.push(format!(
                "  {name} : valeur {value} contre {expected_value}, cartes {card_values:?} contre {expected_cards:?}, \
                 {states} états contre {expected_states}"
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
