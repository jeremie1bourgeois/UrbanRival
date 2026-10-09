//! Le solveur de matrices donne-t-il la valeur que donne SciPy ?
//!
//! `data/nash_expected.json` (écrit par `scripts/build_nash_expected.py`) : des matrices tirées au hasard, de 1 × 1 à
//! 23 × 92, aux valeurs quelconques ou à nombreuses égalités, et leur valeur selon SciPy (HiGHS). Une matrice peut
//! avoir plusieurs équilibres : on compare la **valeur**, pas les stratégies ; que les stratégies trouvées soient un
//! équilibre, le solveur le vérifie lui-même à chaque résolution (écart à l'équilibre).

use serde_json::Value;
use ur_engine::nash::Solver;

/// SciPy (HiGHS) résout à ~1e-9 près.
const AGREEMENT: f64 = 1e-7;

#[test]
fn chaque_matrice_a_la_valeur_que_donne_scipy() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/nash_expected.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/nash_expected.json introuvable");
    let expected: Value = serde_json::from_str(&contents).expect("data/nash_expected.json illisible");
    let matrices = expected.as_array().expect("liste de matrices attendue");
    assert!(!matrices.is_empty());

    let mut solver = Solver::new();
    let mut divergent = Vec::new();
    let (mut pure, mut largest_difference) = (0, 0.0f64);
    for matrix in matrices {
        let rows = matrix["rows"].as_u64().unwrap() as usize;
        let cols = matrix["cols"].as_u64().unwrap() as usize;
        let values: Vec<f64> = matrix["values"]
            .as_array()
            .unwrap()
            .iter()
            .map(|value| value.as_f64().unwrap())
            .collect();
        let scipy = matrix["value"].as_f64().unwrap();
        let solution = solver.solve(&values, rows, cols);
        let difference = (solution.value - scipy).abs();
        largest_difference = largest_difference.max(difference);
        pure += solution.pure as usize;
        if difference > AGREEMENT {
            divergent.push(format!(
                "  {} : {} contre {scipy} pour SciPy",
                matrix["name"], solution.value
            ));
        }
    }
    eprintln!(
        "{} matrices, dont {pure} résolues par un point-selle ; plus grand écart à SciPy : {largest_difference:e}",
        matrices.len()
    );
    assert!(
        divergent.is_empty(),
        "valeurs différentes de SciPy :\n{}",
        divergent.join("\n")
    );
}
