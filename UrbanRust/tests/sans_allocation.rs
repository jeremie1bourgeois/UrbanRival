//! Rien n'est alloué pendant un round, un bloc de mises, ni pour les coups légaux, la fin de partie et la résolution
//! d'une matrice ou de ses équilibres (une fois les tampons du solveur dimensionnés).
//!
//! La recherche appelle ces fonctions des milliards de fois : une allocation par appel coûterait plus que le round
//! lui-même. Ce binaire de test installe un allocateur qui compte les allocations **du fil courant** (le lanceur de
//! tests et les autres fils ne s'y mêlent pas) ; le corpus est chargé hors des zones mesurées. Les blocs mesurés sont
//! ceux d'`aleatoire` (mains réalistes) et tous ceux dont le deck porte une condition Bet (le chemin des tranches) :
//! les autres n'exercent pas de chemin de code de plus.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::Cell;
use std::collections::HashSet;
use std::hint::black_box;

use ur_engine::contract::Deck;
use ur_engine::game::{legal_actions, terminal};
use ur_engine::nash::Solver;
use ur_engine::round::{play, play_block};
use ur_engine::vocabulary::conditions;

const FAMILIES: [&str; 8] = [
    "solo", "interactions", "planchers", "persistants", "leaders", "oculus", "combat", "aleatoire",
];

thread_local! {
    // initialisé sans allocation : l'allocateur le lit
    static ALLOCATIONS: Cell<usize> = const { Cell::new(0) };
}

struct CountingAllocator;

impl CountingAllocator {
    fn count() {
        // `try_with` : pendant la destruction d'un fil, le compteur n'existe plus
        let _ = ALLOCATIONS.try_with(|count| count.set(count.get() + 1));
    }
}

unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        Self::count();
        unsafe { System.alloc(layout) }
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        Self::count();
        unsafe { System.alloc_zeroed(layout) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        Self::count();
        unsafe { System.realloc(ptr, layout, new_size) }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        unsafe { System.dealloc(ptr, layout) }
    }
}

#[global_allocator]
static ALLOCATOR: CountingAllocator = CountingAllocator;

/// Le nombre d'allocations faites par le fil courant pendant `work`.
fn allocations_during(work: impl FnOnce()) -> usize {
    let before = ALLOCATIONS.with(Cell::get);
    work();
    ALLOCATIONS.with(Cell::get) - before
}

#[test]
fn le_compteur_voit_une_allocation() {
    assert_eq!(allocations_during(|| drop(black_box(Vec::<u8>::with_capacity(1)))), 1);
}

#[test]
fn un_round_n_alloue_rien() {
    let families: Vec<_> = FAMILIES.iter().map(|name| corpus::read_family(name)).collect();
    let allocations = allocations_during(|| {
        for family in &families {
            for entry in &family.entries {
                let deck = &family.decks[entry.deck].deck;
                black_box(play(
                    black_box(deck),
                    black_box(&entry.state),
                    entry.ally_action,
                    entry.enemy_action,
                ));
            }
        }
    });
    assert_eq!(allocations, 0, "allocations pendant les rounds du corpus");
}

#[test]
fn un_bloc_de_mises_n_alloue_rien() {
    let families: Vec<_> = FAMILIES.iter().map(|name| corpus::read_family(name)).collect();
    let mut seen = HashSet::new();
    let mut blocks = Vec::new();
    for (index, family) in families.iter().enumerate() {
        for entry in &family.entries {
            let deck = &family.decks[entry.deck].deck;
            let cards = (entry.ally_action.card as usize, entry.enemy_action.card as usize);
            if (FAMILIES[index] == "aleatoire" || has_bet_condition(deck))
                && seen.insert((index, entry.deck, entry.state, cards))
            {
                blocks.push((deck, entry.state, cards));
            }
        }
    }
    let allocations = allocations_during(|| {
        for (deck, state, (ally_card, enemy_card)) in &blocks {
            play_block(
                black_box(deck),
                black_box(state),
                *ally_card,
                *enemy_card,
                |ally, enemy, next, outcome| {
                    black_box((ally, enemy, next, outcome));
                },
            );
        }
    });
    assert_eq!(allocations, 0, "allocations pendant {} blocs de mises", blocks.len());
}

#[test]
fn les_coups_legaux_et_la_fin_de_partie_n_allouent_rien() {
    let entries = corpus::read_rules();
    let allocations = allocations_during(|| {
        for entry in &entries {
            let state = black_box(&entry.state);
            legal_actions(&state.ally)
                .chain(legal_actions(&state.enemy))
                .for_each(|action| {
                    black_box(action);
                });
            black_box(terminal(state));
        }
    });
    assert_eq!(allocations, 0, "allocations pour les coups légaux ou la fin de partie");
}

#[test]
fn un_solveur_reutilise_n_alloue_rien() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/nash_expected.json"
    );
    let expected: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(path).expect("data/nash_expected.json introuvable")).unwrap();
    let matrices: Vec<(Vec<f64>, usize, usize)> = expected
        .as_array()
        .unwrap()
        .iter()
        .map(|matrix| {
            let values = matrix["values"]
                .as_array()
                .unwrap()
                .iter()
                .map(|value| value.as_f64().unwrap())
                .collect();
            (
                values,
                matrix["rows"].as_u64().unwrap() as usize,
                matrix["cols"].as_u64().unwrap() as usize,
            )
        })
        .collect();
    let mut solver = Solver::new();
    for (values, rows, cols) in &matrices {
        // dimensionne les tampons
        solver.solve(values, *rows, *cols);
        solver.equilibria(values, *rows, *cols);
    }
    let allocations = allocations_during(|| {
        for (values, rows, cols) in &matrices {
            black_box(solver.solve(black_box(values), *rows, *cols).value);
            black_box(solver.equilibria(black_box(values), *rows, *cols).value);
        }
    });
    assert_eq!(
        allocations, 0,
        "allocations en résolvant des matrices avec un solveur déjà dimensionné"
    );
}

fn has_bet_condition(deck: &Deck) -> bool {
    deck.ally
        .iter()
        .chain(&deck.enemy)
        .flat_map(|card| [card.ability, card.bonus])
        .flatten()
        .any(|capacity| capacity.conditions & 1 << conditions::BET != 0)
}
