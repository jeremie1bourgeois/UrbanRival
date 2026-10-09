//! Le bloc de mises redonne-t-il, case par case, exactement le round simple ?
//!
//! Chaque bloc distinct du corpus — un état, une carte alliée, une carte ennemie : ~88 000 blocs, ~29 millions de
//! cases — est joué par `play_block` ; chaque case doit égaler `play` sur les mêmes coups, et les cases arriver dans
//! l'ordre des coups légaux, ligne par ligne. Les contextes « mise-N » du corpus exercent les tranches de mises. Le
//! travail est réparti sur tous les cœurs.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::collections::HashSet;
use std::thread;

use ur_engine::contract::{Action, Deck, State};
use ur_engine::game::card_actions;
use ur_engine::round::{play, play_block};

const FAMILIES: [&str; 8] = [
    "solo", "interactions", "planchers", "persistants", "leaders", "oculus", "combat", "aleatoire",
];

/// Un état et une paire de cartes : un bloc de mises.
struct Block<'a> {
    deck: &'a Deck,
    state: State,
    ally_card: usize,
    enemy_card: usize,
}

#[test]
fn chaque_case_du_bloc_egale_le_round_simple() {
    let families: Vec<_> = FAMILIES.iter().map(|name| corpus::read_family(name)).collect();
    let mut seen = HashSet::new();
    let mut blocks = Vec::new();
    for (family_index, family) in families.iter().enumerate() {
        for entry in &family.entries {
            let (ally_card, enemy_card) = (entry.ally_action.card as usize, entry.enemy_action.card as usize);
            if seen.insert((family_index, entry.deck, entry.state, ally_card, enemy_card)) {
                blocks.push(Block {
                    deck: &family.decks[entry.deck].deck,
                    state: entry.state,
                    ally_card,
                    enemy_card,
                });
            }
        }
    }

    let threads = thread::available_parallelism().map_or(1, |count| count.get());
    let divergent: Vec<String> = thread::scope(|scope| {
        let workers: Vec<_> = blocks
            .chunks(blocks.len().div_ceil(threads))
            .map(|chunk| scope.spawn(move || chunk.iter().filter_map(divergence).collect::<Vec<_>>()))
            .collect();
        workers.into_iter().flat_map(|worker| worker.join().unwrap()).collect()
    });
    assert!(
        divergent.is_empty(),
        "{} blocs sur {} divergent du round simple :\n{}",
        divergent.len(),
        blocks.len(),
        divergent[..divergent.len().min(5)].join("\n")
    );
}

/// Le constat d'un bloc qui diverge (cases fausses, hors d'ordre ou manquantes), None s'il est identique.
fn divergence(block: &Block) -> Option<String> {
    let expected: Vec<(Action, Action)> = card_actions(&block.state.ally, block.ally_card)
        .flat_map(|ally| card_actions(&block.state.enemy, block.enemy_card).map(move |enemy| (ally, enemy)))
        .collect();
    let mut visited = 0;
    let mut wrong = 0;
    let mut first = None;
    play_block(
        block.deck,
        &block.state,
        block.ally_card,
        block.enemy_card,
        |ally, enemy, next_state, outcome| {
            let simple = play(block.deck, &block.state, ally, enemy);
            if expected.get(visited) != Some(&(ally, enemy)) || simple != (*next_state, *outcome) {
                wrong += 1;
                first.get_or_insert_with(|| {
                    format!(
                        "    case {ally:?} / {enemy:?}\n    bloc  {:?}\n    round {simple:?}",
                        (next_state, outcome)
                    )
                });
            }
            visited += 1;
        },
    );
    (wrong > 0 || visited != expected.len()).then(|| {
        format!(
            "  {:?}, cartes {} / {} : {wrong} cases fausses, {visited} visitées sur {}\n{}",
            block.state,
            block.ally_card,
            block.enemy_card,
            expected.len(),
            first.unwrap_or_default()
        )
    })
}
