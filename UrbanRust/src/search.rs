//! La recherche exacte : la valeur d'un état selon `docs/IA.md` § 5.1, avec une mémo.
//!
//! V(état) vaut 1 / 0,5 / 0 si la partie est finie. Sinon, le premier joueur F choisit sa carte (publique), puis F mise
//! et S choisit carte et mise sans voir la mise de F : pour chaque carte de F, un jeu matriciel — lignes = mises de F,
//! colonnes = (carte, mise) de S dans l'ordre des coups légaux, cases = V de l'état suivant pour F — ; F prend la carte
//! de meilleure valeur. V est rendue pour l'allié. Les matrices se remplissent par blocs de mises (une carte de F
//! contre une carte de S) ; la référence est `scripts/build_search_expected.py`, en Python (`tests/recherche.rs`).

use std::collections::HashMap;

use crate::contract::{Deck, State, HAND_SIZE};
use crate::game::{card_actions, terminal};
use crate::nash::Solver;
use crate::round::play_block;

/// La recherche sur un deck : la mémo garde la valeur de chaque état déjà résolu.
pub struct Search<'a> {
    deck: &'a Deck,
    memo: HashMap<State, f64>,
    solver: Solver,
}

impl<'a> Search<'a> {
    pub fn new(deck: &'a Deck) -> Self {
        Search { deck, memo: HashMap::new(), solver: Solver::new() }
    }

    /// V(état) pour l'allié.
    pub fn value(&mut self, state: &State) -> f64 {
        if let Some(end) = terminal(state) {
            return end;
        }
        if let Some(&known) = self.memo.get(state) {
            return known;
        }
        let best = self
            .card_values(state)
            .into_iter()
            .flatten()
            .fold(f64::NEG_INFINITY, f64::max);
        let value = if state.ally_first { best } else { 1.0 - best };
        self.memo.insert(*state, value);
        value
    }

    /// Pour chaque carte de la main du premier joueur, la valeur pour lui de son jeu de mises ; None si jouée.
    pub fn card_values(&mut self, state: &State) -> [Option<f64>; HAND_SIZE] {
        let ally_first = state.ally_first;
        let (first, second) = if ally_first {
            (&state.ally, &state.enemy)
        } else {
            (&state.enemy, &state.ally)
        };
        let reply_cards: Vec<usize> = (0..HAND_SIZE).filter(|&card| !second.has_played(card)).collect();
        let cols: usize = reply_cards.iter().map(|&card| card_actions(second, card).count()).sum();
        let mut values = [None; HAND_SIZE];
        for card in (0..HAND_SIZE).filter(|&card| !first.has_played(card)) {
            let rows = card_actions(first, card).count();
            let mut matrix = vec![0.0; rows * cols];
            let mut col_offset = 0;
            for &reply_card in &reply_cards {
                let bets = card_actions(second, reply_card).count();
                let (ally_card, enemy_card) = if ally_first {
                    (card, reply_card)
                } else {
                    (reply_card, card)
                };
                let mut next_states = Vec::with_capacity(rows * bets);
                play_block(self.deck, state, ally_card, enemy_card, |_, _, next_state, _| {
                    next_states.push(*next_state)
                });
                // le bloc va ligne par ligne, lignes = mises de l'allié : transposé quand F est l'ennemi
                let enemy_bets = if ally_first { bets } else { rows };
                for (index, next_state) in next_states.iter().enumerate() {
                    let (ally_bet, enemy_bet) = (index / enemy_bets, index % enemy_bets);
                    let (row, bet) = if ally_first {
                        (ally_bet, enemy_bet)
                    } else {
                        (enemy_bet, ally_bet)
                    };
                    let value = self.value(next_state);
                    matrix[row * cols + col_offset + bet] = if ally_first { value } else { 1.0 - value };
                }
                col_offset += bets;
            }
            values[card] = Some(self.solver.solve(&matrix, rows, cols).value);
        }
        values
    }

    /// Le nombre d'états non terminaux résolus et gardés en mémo.
    pub fn solved_states(&self) -> usize {
        self.memo.len()
    }
}
