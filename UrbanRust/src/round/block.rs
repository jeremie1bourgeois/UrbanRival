//! Le bloc de mises : toutes les combinaisons de mises d'une paire de cartes, le premier étage du round calculé une
//! fois par tranche de mises au lieu d'une fois par case.
//!
//! Le premier étage (`Round::first_stage`) ne lit la mise que par les conditions « Bet > N / Bet < N ». Deux mises qui
//! donnent la même réponse à chacune de ces conditions — la même **signature** — donnent donc le même premier étage :
//! elles sont dans la même tranche. Les conditions viennent toutes des capacités imprimées du deck (pouvoir, bonus
//! copié par un Oculus, capacité Team du Leader, copie de l'adversaire) ; la signature les prend toutes, celles des
//! cartes non jouées comprises. C'est parfois une tranche de trop, jamais une de moins.

use super::{bet_condition_met, bit, Round};
use crate::contract::{Action, CompiledCapacity, Deck, Outcome, State, HAND_SIZE};
use crate::game::card_actions;
use crate::vocabulary::conditions;

/// Au plus une condition Bet par capacité imprimée du deck : deux camps, 4 cartes, un pouvoir et un bonus.
const MAX_BET_CONDITIONS: usize = 2 * HAND_SIZE * 2;
/// N conditions à seuil découpent les mises en au plus N + 1 tranches.
const MAX_TRANCHES: usize = MAX_BET_CONDITIONS + 1;

/// Joue toutes les combinaisons de mises de la carte `ally_card` contre la carte `enemy_card` : `visit` reçoit chaque
/// case, ligne par ligne — lignes = coups de la carte alliée, colonnes = coups de la carte ennemie, chacun dans l'ordre
/// de `legal_actions` —, avec l'état suivant et l'issue du combat, exactement ceux de `play`. Rien n'est alloué.
pub fn play_block(
    deck: &Deck,
    state: &State,
    ally_card: usize,
    enemy_card: usize,
    mut visit: impl FnMut(Action, Action, &State, &Outcome),
) {
    let bets = BetConditions::of(deck);
    // premiers étages de la tranche alliée en cours, par signature ennemie : les lignes d'une tranche se suivent,
    // les mises croissant
    let mut prepared: [Option<(u32, Round)>; MAX_TRANCHES] = [None; MAX_TRANCHES];
    let mut ally_signature = None;
    for ally in card_actions(&state.ally, ally_card) {
        let signature = bets.signature(ally.pillz);
        if ally_signature != Some(signature) {
            ally_signature = Some(signature);
            prepared = [None; MAX_TRANCHES];
        }
        for enemy in card_actions(&state.enemy, enemy_card) {
            let first_stage = first_stage_of(&mut prepared, bets.signature(enemy.pillz), || {
                let mut round = Round::new(deck, state, [ally, enemy]);
                round.first_stage();
                round
            });
            let mut round = first_stage;
            round.place_bets(state, [ally, enemy]);
            round.second_stage();
            let (next_state, outcome) = round.finish();
            visit(ally, enemy, &next_state, &outcome);
        }
    }
}

/// Le premier étage de la tranche ennemie `signature`, calculé à sa première case puis repris pour les suivantes.
fn first_stage_of<'a>(
    prepared: &mut [Option<(u32, Round<'a>)>; MAX_TRANCHES],
    signature: u32,
    compute: impl FnOnce() -> Round<'a>,
) -> Round<'a> {
    for entry in prepared.iter_mut() {
        match entry {
            Some((known, round)) if *known == signature => return *round,
            Some(_) => continue,
            None => {
                let round = compute();
                *entry = Some((signature, round));
                return round;
            }
        }
    }
    unreachable!("plus de {MAX_TRANCHES} tranches de mises")
}

/// Les conditions Bet des capacités imprimées du deck : les `count` premières cases de `capacities`.
struct BetConditions {
    capacities: [Option<CompiledCapacity>; MAX_BET_CONDITIONS],
    count: usize,
}

impl BetConditions {
    fn of(deck: &Deck) -> Self {
        let mut capacities = [None; MAX_BET_CONDITIONS];
        let mut count = 0;
        let printed = deck
            .ally
            .iter()
            .chain(&deck.enemy)
            .flat_map(|card| [card.ability, card.bonus])
            .flatten();
        for (slot, capacity) in printed
            .filter(|capacity| capacity.conditions & bit(conditions::BET) != 0)
            .enumerate()
        {
            capacities[slot] = Some(capacity);
            count += 1;
        }
        BetConditions { capacities, count }
    }

    /// Bit i levé : la mise remplit la i-ème condition. Calculée à chaque case : seules les conditions réelles se
    /// parcourent, aucune le plus souvent (README, « Optimisations en place »).
    fn signature(&self, bet: i16) -> u32 {
        let mut signature = 0;
        for (index, capacity) in self.capacities[..self.count].iter().flatten().enumerate() {
            if bet_condition_met(capacity, bet) {
                signature |= 1 << index;
            }
        }
        signature
    }
}
