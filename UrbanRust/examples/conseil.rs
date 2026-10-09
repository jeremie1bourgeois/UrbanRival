//! Le conseil d'un round : lit sur l'entrée standard un deck, un état et, si l'ennemi joue en premier, la carte qu'il a
//! posée ; écrit sur la sortie standard, en JSON, la valeur exacte de l'état pour l'allié et sa stratégie d'équilibre
//! pour ce round. Appelé par `UrbanPy/Backend_fastAPI/scripts/conseil_nash.py`, qui lui passe la partie en cours.
//!
//! Entrée : `{"deck": …, "state": …, "enemy_card": null | indice}`, deck et état écrits comme dans le banc d'essai
//! (`dataclasses.asdict`). Sortie : `{"value", "cards", "strategy", "states", "seconds"}` — `cards`, la valeur de
//! chaque carte de l'allié quand il joue en premier (null sinon) ; `strategy`, les coups (carte, pillz_fight, fury) que
//! l'équilibre joue, avec leur probabilité.
//!
//! La matrice du round se remplit comme dans `Search::card_values`, mais par coups plutôt que par indices : quand
//! l'allié joue en premier, sa valeur doit égaler celle que donne la recherche, et le programme s'arrête sinon.

#[allow(dead_code)] // le conseil ne lit qu'un deck et un état
#[path = "../tests/corpus/mod.rs"]
mod corpus;

use std::io::Read;
use std::time::Instant;

use rayon::prelude::*;
use serde_json::{json, Value};
use ur_engine::contract::{Action, Deck, State, HAND_SIZE};
use ur_engine::game::card_actions;
use ur_engine::nash::{Solver, TOLERANCE};
use ur_engine::round::play_block;
use ur_engine::search::Search;

/// Sous ce seuil, un coup n'est pas joué par l'équilibre.
const MIN_PROBABILITY: f64 = 1e-9;

fn main() {
    let mut input = String::new();
    std::io::stdin()
        .read_to_string(&mut input)
        .expect("entrée standard lisible");
    let request: Value = serde_json::from_str(&input).expect("entrée en JSON");
    let deck = corpus::parse_deck(&request["deck"]).deck;
    let state = corpus::parse_state(&request["state"]);
    let enemy_card = request["enemy_card"].as_u64().map(|card| card as usize);

    let start = Instant::now();
    let search = Search::parallel(&deck);
    let (value, cards, strategy) = match (state.ally_first, enemy_card) {
        (true, None) => lead(&search, &deck, &state),
        (false, Some(card)) => reply(&search, &deck, &state, card),
        _ => panic!("enemy_card attendue si et seulement si l'ennemi joue en premier"),
    };
    let strategy: Vec<Value> = strategy
        .into_iter()
        .filter(|&(_, probability)| probability > MIN_PROBABILITY)
        .map(|(action, probability)| {
            json!({"card": action.card, "pillz": action.pillz, "fury": action.fury, "probability": probability})
        })
        .collect();
    let answer = json!({
        "value": value,
        "cards": cards,
        "strategy": strategy,
        "states": search.solved_states(),
        "seconds": start.elapsed().as_secs_f64(),
    });
    println!("{answer}");
}

/// L'allié joue en premier : la valeur de chacune de ses cartes, puis les mises de la meilleure.
fn lead(search: &Search, deck: &Deck, state: &State) -> (f64, Value, Vec<(Action, f64)>) {
    let values = search.card_values(state);
    let best = (0..HAND_SIZE)
        .filter(|&card| values[card].is_some())
        .max_by(|&a, &b| values[a].unwrap().total_cmp(&values[b].unwrap()))
        .expect("une carte en main");
    let (rows, cols, matrix) = bet_game(search, deck, state, best);
    let mut solver = Solver::new();
    let solution = solver.solve(&matrix, rows.len(), cols.len());
    assert!(
        (solution.value - values[best].unwrap()).abs() <= TOLERANCE,
        "la matrice du conseil ({}) ne redonne pas la valeur de la recherche ({:?})",
        solution.value,
        values[best]
    );
    let cards: Vec<Value> = (0..HAND_SIZE)
        .filter_map(|card| values[card].map(|value| json!({"card": card, "value": value})))
        .collect();
    let strategy = rows.into_iter().zip(solution.rows.iter().copied()).collect();
    (solution.value, Value::from(cards), strategy)
}

/// L'ennemi a posé `enemy_card` : la carte et la mise de l'allié, ensemble.
fn reply(search: &Search, deck: &Deck, state: &State, enemy_card: usize) -> (f64, Value, Vec<(Action, f64)>) {
    let (rows, cols, matrix) = bet_game(search, deck, state, enemy_card);
    let mut solver = Solver::new();
    let solution = solver.solve(&matrix, rows.len(), cols.len());
    let strategy = cols.into_iter().zip(solution.cols.iter().copied()).collect();
    (1.0 - solution.value, Value::Null, strategy)
}

/// Le jeu de mises de la carte `card` du premier joueur F : lignes = ses coups avec cette carte, colonnes = les coups
/// du second (carte et mise), cases = V de l'état suivant pour F.
fn bet_game(search: &Search, deck: &Deck, state: &State, card: usize) -> (Vec<Action>, Vec<Action>, Vec<f64>) {
    let ally_first = state.ally_first;
    let (first, second) = if ally_first {
        (&state.ally, &state.enemy)
    } else {
        (&state.enemy, &state.ally)
    };
    let rows: Vec<Action> = card_actions(first, card).collect();
    let reply_cards: Vec<usize> = (0..HAND_SIZE).filter(|&reply| !second.has_played(reply)).collect();
    let cols: Vec<Action> = reply_cards
        .iter()
        .flat_map(|&reply| card_actions(second, reply))
        .collect();

    let mut cells = Vec::with_capacity(rows.len() * cols.len());
    for &reply in &reply_cards {
        let (ally_card, enemy_card) = if ally_first { (card, reply) } else { (reply, card) };
        play_block(deck, state, ally_card, enemy_card, |ally, enemy, next_state, _| {
            let (first_action, second_action) = if ally_first { (ally, enemy) } else { (enemy, ally) };
            let row = rows
                .iter()
                .position(|&action| action == first_action)
                .expect("coup de F");
            let col = cols
                .iter()
                .position(|&action| action == second_action)
                .expect("coup de S");
            cells.push((row * cols.len() + col, *next_state));
        });
    }
    let values: Vec<f64> = cells
        .par_iter()
        .map(|(_, next_state)| search.value(next_state))
        .collect();
    let mut matrix = vec![f64::NAN; rows.len() * cols.len()];
    for ((cell, _), value) in cells.iter().zip(values) {
        matrix[*cell] = if ally_first { value } else { 1.0 - value };
    }
    assert!(
        matrix.iter().all(|value| !value.is_nan()),
        "case de matrice non remplie"
    );
    (rows, cols, matrix)
}
