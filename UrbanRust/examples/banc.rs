//! Le banc d'essai (`docs/PLAN-MOTEUR.md`, étapes 3.1 et 3.2) : résout les états de `data/engine_bench.json` et
//! affiche les indicateurs du plan (§ « Ce qu'on compte ») pour chaque round de départ. Une branche est une case de
//! matrice, un couple de coups simulé ; un nœud, un état dont on calcule la valeur. La somme des valeurs sert
//! d'empreinte : une optimisation qui la change a changé un résultat.
//!
//! Usage, depuis `UrbanRust` : `cargo run --release --example banc`, ou avec les rounds à mesurer, par exemple
//! `cargo run --release --example banc -- 4 3 2` (par défaut, 4, 3, 2 et 1). Le round 1, la partie entière, ne se
//! mesure que sur les `ROUND_1_GAMES` premières parties, et sur tous les cœurs : une main y prend une dizaine de
//! secondes sur un Mac M4.

#[allow(dead_code)] // le banc ne lit que des decks et des états
#[path = "../tests/corpus/mod.rs"]
mod corpus;

use std::time::{Duration, Instant};

use corpus::BenchGame;
use ur_engine::contract::State;
use ur_engine::game::legal_actions;
use ur_engine::search::Search;

const ROUND_1_GAMES: usize = 4;
/// Les rounds 3 et 4 se résolvent en quelques millisecondes ou microsecondes : leur lot est rejoué jusqu'à cette
/// durée, pour une moyenne stable.
const MIN_DURATION: Duration = Duration::from_secs(1);

fn main() {
    let rounds = match std::env::args()
        .skip(1)
        .map(|arg| arg.parse())
        .collect::<Result<Vec<usize>, _>>()
    {
        Ok(rounds) if rounds.is_empty() => vec![4, 3, 2, 1],
        Ok(rounds) if rounds.iter().all(|round| (1..=4).contains(round)) => rounds,
        _ => panic!("arguments attendus : des rounds de départ, de 1 à 4"),
    };
    let games = corpus::read_bench();
    let threads = rayon::current_num_threads();
    println!(
        "Banc : {} parties (data/engine_bench.json), {threads} fils ; le round 1 sur les {ROUND_1_GAMES} premières",
        games.len()
    );
    println!(
        "{:<5} {:<10} {:>5} {:>10} {:>10} {:>10} {:>11} {:>11} {:>11} {:>11} {:>9} {:>16}",
        "round",
        "mode",
        "états",
        "moyenne",
        "max",
        "nœuds/état",
        "nœuds/s",
        "branches/é.",
        "branches/s",
        "par cœur",
        "mémo max",
        "Σ valeurs"
    );
    for round in rounds {
        let modes: &[bool] = match round {
            1 => &[true],
            2 => &[false, true],
            _ => &[false],
        };
        let games = if round == 1 {
            &games[..ROUND_1_GAMES]
        } else {
            &games[..]
        };
        for &parallel in modes {
            let measure = measure(games, round, parallel);
            print_row(round, parallel, threads, &measure);
        }
    }
}

/// Ce qu'a coûté la résolution d'un lot d'états, rejoué `passes` fois.
#[derive(Default)]
struct Measure {
    states: usize,
    passes: usize,
    total: Duration,
    max: Duration,
    nodes: usize,
    branches: usize,
    memo_bytes: usize,
    values: f64,
}

/// Résout l'état de début du round `round` de chaque partie, chacun avec sa propre recherche, sur un fil ou sur tous
/// les cœurs ; les rounds 3 et 4 sont rejoués jusqu'à `MIN_DURATION`. Seule la résolution est chronométrée, création
/// de la recherche comprise.
fn measure(games: &[BenchGame], round: usize, parallel: bool) -> Measure {
    let mut measure = Measure::default();
    while measure.passes == 0 || (round >= 3 && measure.total < MIN_DURATION) {
        for game in games {
            let state = &game.states[round - 1];
            let start = Instant::now();
            let search = if parallel {
                Search::parallel(&game.deck)
            } else {
                Search::new(&game.deck)
            };
            let value = search.value(state);
            let elapsed = start.elapsed();
            measure.total += elapsed;
            measure.max = measure.max.max(elapsed);
            if measure.passes == 0 {
                measure.states += 1;
                measure.nodes += search.solved_states();
                measure.branches += search.solved().iter().map(|(state, _)| branches(state)).sum::<usize>();
                measure.memo_bytes = measure.memo_bytes.max(search.memo_bytes());
                measure.values += value;
            }
        }
        measure.passes += 1;
    }
    measure
}

/// Les branches d'un état résolu : les cases de ses matrices, chacune un coup de chaque camp.
fn branches(state: &State) -> usize {
    legal_actions(&state.ally).count() * legal_actions(&state.enemy).count()
}

fn print_row(round: usize, parallel: bool, threads: usize, measure: &Measure) {
    let solves = (measure.states * measure.passes) as f64;
    let seconds = measure.total.as_secs_f64() / measure.passes as f64; // une passe sur le lot
    let mode = if parallel {
        format!("{threads} fils")
    } else {
        "1 fil".to_string()
    };
    let cores = if parallel { threads as f64 } else { 1.0 };
    let branches_per_second = measure.branches as f64 / seconds;
    println!(
        "{:<5} {:<10} {:>5} {:>10} {:>10} {:>10} {:>11} {:>11} {:>11} {:>11} {:>9} {:>16.12}",
        round,
        mode,
        measure.states,
        duration(measure.total.as_secs_f64() / solves),
        duration(measure.max.as_secs_f64()),
        count(measure.nodes as f64 / measure.states as f64),
        count(measure.nodes as f64 / seconds),
        count(measure.branches as f64 / measure.states as f64),
        count(branches_per_second),
        count(branches_per_second / cores),
        format!("{:.1} Mo", measure.memo_bytes as f64 / 1e6),
        measure.values
    );
}

fn duration(seconds: f64) -> String {
    match seconds {
        s if s < 1e-3 => format!("{:.1} µs", s * 1e6),
        s if s < 1.0 => format!("{:.1} ms", s * 1e3),
        s => format!("{s:.2} s"),
    }
}

fn count(number: f64) -> String {
    match number {
        n if n < 1e3 => format!("{n:.0}"),
        n if n < 1e6 => format!("{:.1} k", n / 1e3),
        n => format!("{:.2} M", n / 1e6),
    }
}
