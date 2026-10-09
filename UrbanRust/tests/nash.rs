//! Le solveur de matrices donne-t-il ce que donne SciPy ?
//!
//! `data/nash_expected.json` (écrit par `scripts/build_nash_expected.py`) : des matrices tirées au hasard, de 1 × 1 à
//! 23 × 92, aux valeurs quelconques ou à nombreuses égalités ; leur valeur selon SciPy (HiGHS), et pour chaque coup de
//! chaque joueur sa plus forte probabilité dans une stratégie optimale. Une matrice peut avoir plusieurs équilibres :
//! on compare ces nombres, uniques, et pas les stratégies ; que les stratégies trouvées soient des équilibres, le
//! solveur le vérifie lui-même à chaque résolution.

use serde_json::Value;
use ur_engine::nash::Solver;

/// SciPy (HiGHS) résout à ~1e-9 près.
const AGREEMENT: f64 = 1e-7;

/// Une matrice du fichier et ce qu'en dit SciPy.
struct Expected {
    name: String,
    rows: usize,
    cols: usize,
    values: Vec<f64>,
    value: f64,
    row_best: Vec<f64>,
    col_best: Vec<f64>,
}

fn expected_matrices() -> Vec<Expected> {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/nash_expected.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/nash_expected.json introuvable");
    let expected: Value = serde_json::from_str(&contents).expect("data/nash_expected.json illisible");
    let numbers = |list: &Value| -> Vec<f64> { list.as_array().unwrap().iter().map(|n| n.as_f64().unwrap()).collect() };
    let matrices: Vec<Expected> = expected
        .as_array()
        .expect("liste de matrices attendue")
        .iter()
        .map(|matrix| Expected {
            name: matrix["name"].as_str().unwrap().to_string(),
            rows: matrix["rows"].as_u64().unwrap() as usize,
            cols: matrix["cols"].as_u64().unwrap() as usize,
            values: numbers(&matrix["values"]),
            value: matrix["value"].as_f64().unwrap(),
            row_best: numbers(&matrix["row_best"]),
            col_best: numbers(&matrix["col_best"]),
        })
        .collect();
    assert!(!matrices.is_empty());
    matrices
}

#[test]
fn chaque_matrice_a_la_valeur_que_donne_scipy() {
    let matrices = expected_matrices();
    let mut solver = Solver::new();
    let mut divergent = Vec::new();
    let (mut pure, mut largest_difference) = (0, 0.0f64);
    for matrix in &matrices {
        let solution = solver.solve(&matrix.values, matrix.rows, matrix.cols);
        let difference = (solution.value - matrix.value).abs();
        largest_difference = largest_difference.max(difference);
        pure += solution.pure as usize;
        if difference > AGREEMENT {
            divergent.push(format!(
                "  {} : {} contre {} pour SciPy",
                matrix.name, solution.value, matrix.value
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

/// « Chaque coup jouable dans un équilibre apparaît » : la plus forte probabilité de chaque coup, celle de SciPy.
#[test]
fn chaque_coup_a_la_plus_forte_probabilite_que_donne_scipy() {
    let matrices = expected_matrices();
    let mut solver = Solver::new();
    let mut divergent = Vec::new();
    let (mut never_played, mut compared, mut largest_difference) = (0, 0, 0.0f64);
    for matrix in &matrices {
        let equilibria = solver.equilibria(&matrix.values, matrix.rows, matrix.cols);
        let rows_never_played = (0..matrix.rows)
            .filter(|&row| equilibria.row_strategy(row)[row] == 0.0)
            .count();
        let cols_never_played = (0..matrix.cols)
            .filter(|&col| equilibria.col_strategy(col)[col] == 0.0)
            .count();
        never_played += rows_never_played + cols_never_played;
        let mut compare = |kind: &str, action: usize, found: f64, scipy: f64| {
            let difference = (found - scipy).abs();
            largest_difference = largest_difference.max(difference);
            compared += 1;
            if difference > AGREEMENT {
                divergent.push(format!(
                    "  {} {kind} {action} : {found} contre {scipy} pour SciPy",
                    matrix.name
                ));
            }
        };
        compare("valeur", 0, equilibria.value, matrix.value);
        for row in 0..matrix.rows {
            compare("ligne", row, equilibria.row_strategy(row)[row], matrix.row_best[row]);
        }
        for col in 0..matrix.cols {
            compare("colonne", col, equilibria.col_strategy(col)[col], matrix.col_best[col]);
        }
    }
    eprintln!(
        "{compared} nombres comparés ; {never_played} coups ne sont joués dans aucun équilibre ; plus grand écart à SciPy : \
         {largest_difference:e}"
    );
    assert!(
        divergent.is_empty(),
        "probabilités différentes de SciPy :\n{}",
        divergent[..divergent.len().min(10)].join("\n")
    );
}
