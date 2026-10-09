//! Benchmarks du round, du bloc de mises et du solveur (`docs/PLAN-MOTEUR.md`, étape 3.2), sur des données
//! versionnées. Le round simple et le bloc jouent les mêmes cases : toutes les combinaisons de coups des états du banc
//! d'essai (`data/engine_bench.json`, rounds 1 à 4) ; le débit s'y compte en cases. Le solveur résout les matrices de
//! `data/nash_expected.json` ; le débit s'y compte en matrices. Le banc complet, recherche comprise, est
//! `examples/banc.rs`.
//!
//! Usage, depuis `UrbanRust` : `cargo bench`.

#[allow(dead_code)] // les benchmarks ne lisent que le banc
#[path = "../tests/corpus/mod.rs"]
mod corpus;

use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion, Throughput};
use serde_json::Value;
use ur_engine::contract::{Deck, State, HAND_SIZE};
use ur_engine::game::card_actions;
use ur_engine::nash::Solver;
use ur_engine::round::{play, play_block};

/// Une paire de cartes à jouer depuis un état : un bloc de mises.
struct Block<'a> {
    deck: &'a Deck,
    state: &'a State,
    ally_card: usize,
    enemy_card: usize,
}

fn blocks(games: &[corpus::BenchGame]) -> Vec<Block<'_>> {
    let mut blocks = Vec::new();
    for game in games {
        for state in &game.states {
            for ally_card in (0..HAND_SIZE).filter(|&card| !state.ally.has_played(card)) {
                for enemy_card in (0..HAND_SIZE).filter(|&card| !state.enemy.has_played(card)) {
                    blocks.push(Block { deck: &game.deck, state, ally_card, enemy_card });
                }
            }
        }
    }
    blocks
}

fn round_and_block(criterion: &mut Criterion) {
    let games = corpus::read_bench();
    let blocks = blocks(&games);
    let cells: usize = blocks
        .iter()
        .map(|block| {
            card_actions(&block.state.ally, block.ally_card).count()
                * card_actions(&block.state.enemy, block.enemy_card).count()
        })
        .sum();
    let mut group = criterion.benchmark_group("cases du banc");
    group.throughput(Throughput::Elements(cells as u64));
    group.sample_size(10);
    group.bench_function("round simple", |bencher| {
        bencher.iter(|| {
            for block in &blocks {
                for ally_action in card_actions(&block.state.ally, block.ally_card) {
                    for enemy_action in card_actions(&block.state.enemy, block.enemy_card) {
                        black_box(play(block.deck, block.state, ally_action, enemy_action));
                    }
                }
            }
        })
    });
    group.bench_function("bloc de mises", |bencher| {
        bencher.iter(|| {
            for block in &blocks {
                play_block(
                    block.deck,
                    block.state,
                    block.ally_card,
                    block.enemy_card,
                    |_, _, next, outcome| {
                        black_box((next, outcome));
                    },
                );
            }
        })
    });
    group.finish();
}

fn matrices(criterion: &mut Criterion) {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/nash_expected.json"
    );
    let expected: Value =
        serde_json::from_str(&std::fs::read_to_string(path).expect("data/nash_expected.json introuvable"))
            .expect("data/nash_expected.json illisible");
    let matrices: Vec<(usize, usize, Vec<f64>)> = expected
        .as_array()
        .expect("liste de matrices attendue")
        .iter()
        .map(|matrix| {
            let values = matrix["values"]
                .as_array()
                .unwrap()
                .iter()
                .map(|value| value.as_f64().unwrap())
                .collect();
            (
                matrix["rows"].as_u64().unwrap() as usize,
                matrix["cols"].as_u64().unwrap() as usize,
                values,
            )
        })
        .collect();
    let mut solver = Solver::new();
    let mut group = criterion.benchmark_group("solveur");
    group.throughput(Throughput::Elements(matrices.len() as u64));
    group.bench_function("matrices de nash_expected.json", |bencher| {
        bencher.iter(|| {
            for (rows, cols, values) in &matrices {
                black_box(solver.solve(values, *rows, *cols).value);
            }
        })
    });
    group.finish();
}

criterion_group!(benches, round_and_block, matrices);
criterion_main!(benches);
