//! Le solveur de jeux matriciels à somme nulle : la valeur et un équilibre de Nash d'une matrice dont les lignes sont
//! le joueur qui maximise (`docs/IA.md` § 4.3). Écrit pour les matrices du moteur, petites (au plus ~23 × 92) : la
//! solution pure d'abord (un point-selle, fréquent au round 4), sinon le simplexe. Chaque solution est vérifiée par
//! son écart à l'équilibre. SciPy ne sert qu'aux tests (`tests/nash.rs`).

/// Écart à l'équilibre toléré : les valeurs du jeu sont des probabilités, dans [0, 1].
pub const TOLERANCE: f64 = 1e-9;
/// En deçà, un coefficient du tableau du simplexe compte pour nul.
const PIVOT_EPSILON: f64 = 1e-11;

/// Un équilibre de la matrice. Les stratégies sont des probabilités par ligne et par colonne.
pub struct Solution<'a> {
    pub value: f64,
    pub rows: &'a [f64],
    pub cols: &'a [f64],
    /// Trouvée comme point-selle, sans simplexe.
    pub pure: bool,
    /// Ce que les lignes gagneraient de mieux contre `cols`, moins ce que `rows` leur garantit : 0 à l'équilibre.
    pub gap: f64,
}

/// Les tampons du solveur, dimensionnés au premier appel puis réutilisés : rien n'est alloué ensuite pour des matrices
/// de même taille ou plus petites.
#[derive(Default)]
pub struct Solver {
    rows: Vec<f64>,
    cols: Vec<f64>,
    tableau: Tableau,
}

impl Solver {
    pub fn new() -> Self {
        Self::default()
    }

    /// Résout la matrice `rows × cols`, donnée ligne par ligne. Une solution qui s'écarterait de l'équilibre de plus
    /// de `TOLERANCE`, ou dont la valeur ne serait pas celle que ses stratégies garantissent, est une erreur du
    /// solveur : elle arrête le programme plutôt que d'être rendue.
    pub fn solve(&mut self, matrix: &[f64], rows: usize, cols: usize) -> Solution<'_> {
        assert!(
            rows > 0 && cols > 0 && matrix.len() == rows * cols,
            "matrice {rows} × {cols} mal formée"
        );
        self.rows.clear();
        self.rows.resize(rows, 0.0);
        self.cols.clear();
        self.cols.resize(cols, 0.0);
        let (value, pure) = match saddle_point(matrix, rows, cols) {
            Some((row, col)) => {
                self.rows[row] = 1.0;
                self.cols[col] = 1.0;
                (matrix[row * cols + col], true)
            }
            None => {
                self.tableau.load(matrix, rows, cols);
                self.tableau.optimize(|_| true);
                self.tableau.row_strategy(&mut self.rows);
                self.tableau.col_strategy(&mut self.cols);
                (self.tableau.value(), false)
            }
        };
        let gap = verify(matrix, cols, &self.rows, &self.cols, value);
        Solution { value, rows: &self.rows, cols: &self.cols, pure, gap }
    }
}

/// Le programme linéaire des colonnes d'un jeu décalé (toutes les valeurs ≥ 1, donc une valeur > 0) : maximiser Σ y
/// sous M y ≤ 1, y ≥ 0, en tableau du simplexe. Alors valeur = 1 / Σ y et colonnes = y × valeur ; les lignes sont
/// les variables duales, lues sur les coûts réduits des variables d'écart. Les variables, dans l'ordre des colonnes du
/// tableau : y (une par colonne du jeu), puis un écart par ligne ; la dernière colonne est le second membre.
#[derive(Default)]
struct Tableau {
    rows: usize,
    cols: usize,
    shift: f64,
    cells: Vec<f64>,     // rows × width, ligne par ligne
    objective: Vec<f64>, // coûts réduits des variables, puis la valeur de l'objectif
    basis: Vec<usize>,   // la variable de base de chaque ligne
}

impl Tableau {
    fn width(&self) -> usize {
        self.cols + self.rows + 1
    }

    fn rhs(&self) -> usize {
        self.cols + self.rows
    }

    /// Le jeu `matrix` (`rows × cols`, ligne par ligne) décalé, à l'objectif Σ y, la base étant celle des écarts.
    fn load(&mut self, matrix: &[f64], rows: usize, cols: usize) {
        self.rows = rows;
        self.cols = cols;
        self.shift = 1.0 - matrix.iter().copied().fold(f64::INFINITY, f64::min);
        let (width, rhs) = (self.width(), self.rhs());
        self.cells.clear();
        self.cells.resize(rows * width, 0.0);
        for row in 0..rows {
            for col in 0..cols {
                self.cells[row * width + col] = matrix[row * cols + col] + self.shift;
            }
            self.cells[row * width + cols + row] = 1.0;
            self.cells[row * width + rhs] = 1.0;
        }
        self.objective.clear();
        self.objective.resize(width, 0.0);
        self.objective[..cols].fill(-1.0);
        self.basis.clear();
        self.basis.extend(cols..cols + rows);
    }

    /// Le simplexe jusqu'à l'optimum de l'objectif courant, en ne faisant entrer que les variables `allowed`. Règle de
    /// Bland : entre la première variable de coût réduit négatif ; sort la ligne du plus petit rapport, à égalité
    /// celle dont la variable de base a le plus petit indice. Le simplexe ne peut alors pas cycler, même sur les
    /// matrices à nombreuses égalités.
    fn optimize(&mut self, allowed: impl Fn(usize) -> bool) {
        let (width, rhs) = (self.width(), self.rhs());
        while let Some(entering) = (0..rhs).find(|&col| self.objective[col] < -PIVOT_EPSILON && allowed(col)) {
            let mut leaving: Option<(usize, f64)> = None;
            for row in 0..self.rows {
                let coefficient = self.cells[row * width + entering];
                if coefficient <= PIVOT_EPSILON {
                    continue;
                }
                let ratio = self.cells[row * width + rhs] / coefficient;
                let better = match leaving {
                    None => true,
                    Some((best, best_ratio)) => {
                        ratio < best_ratio - PIVOT_EPSILON
                            || ratio <= best_ratio + PIVOT_EPSILON && self.basis[row] < self.basis[best]
                    }
                };
                if better {
                    leaving = Some((row, ratio));
                }
            }
            let (leaving, _) = leaving.expect("simplexe non borné : impossible sur un jeu décalé à valeurs positives");
            self.pivot(leaving, entering);
        }
    }

    /// La valeur du jeu d'origine, à l'optimum de l'objectif Σ y.
    fn value(&self) -> f64 {
        1.0 / self.objective[self.rhs()] - self.shift
    }

    /// La stratégie des colonnes : y, normalisé.
    fn col_strategy(&self, strategy: &mut [f64]) {
        let (width, rhs) = (self.width(), self.rhs());
        strategy.fill(0.0);
        for row in 0..self.rows {
            if self.basis[row] < self.cols {
                strategy[self.basis[row]] = self.cells[row * width + rhs].max(0.0);
            }
        }
        normalize(strategy);
    }

    /// La stratégie des lignes : les coûts réduits des écarts (les variables duales), normalisés.
    fn row_strategy(&self, strategy: &mut [f64]) {
        for (row, probability) in strategy.iter_mut().enumerate() {
            *probability = self.objective[self.cols + row].max(0.0);
        }
        normalize(strategy);
    }

    fn pivot(&mut self, pivot_row: usize, pivot_col: usize) {
        let width = self.width();
        let pivot = self.cells[pivot_row * width + pivot_col];
        for col in 0..width {
            self.cells[pivot_row * width + col] /= pivot;
        }
        for row in (0..self.rows).filter(|&row| row != pivot_row) {
            let factor = self.cells[row * width + pivot_col];
            if factor != 0.0 {
                for col in 0..width {
                    let pivot_value = self.cells[pivot_row * width + col];
                    self.cells[row * width + col] -= factor * pivot_value;
                }
            }
        }
        let factor = self.objective[pivot_col];
        for col in 0..width {
            self.objective[col] -= factor * self.cells[pivot_row * width + col];
        }
        self.basis[pivot_row] = pivot_col;
    }
}

/// Vérifie que les deux stratégies forment un équilibre de valeur `value` et rend leur écart à l'équilibre ; une
/// solution fausse est une erreur du solveur, qui arrête le programme.
fn verify(matrix: &[f64], cols: usize, row_strategy: &[f64], col_strategy: &[f64], value: f64) -> f64 {
    let (best_row_reply, worst_col_reply) = replies(matrix, cols, row_strategy, col_strategy);
    let gap = best_row_reply - worst_col_reply;
    assert!(
        gap <= TOLERANCE && worst_col_reply - TOLERANCE <= value && value <= best_row_reply + TOLERANCE,
        "solution hors d'équilibre ({} × {cols}) : valeur {value}, entre {worst_col_reply} et {best_row_reply}",
        row_strategy.len()
    );
    gap
}

/// Un point-selle : la ligne du meilleur minimum et la colonne du plus petit maximum, si ces deux valeurs se
/// rejoignent (à `TOLERANCE` près). Ces deux coups purs forment alors un équilibre.
fn saddle_point(matrix: &[f64], rows: usize, cols: usize) -> Option<(usize, usize)> {
    let mut maximin = (0, f64::NEG_INFINITY);
    for row in 0..rows {
        let minimum = matrix[row * cols..(row + 1) * cols]
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min);
        if minimum > maximin.1 {
            maximin = (row, minimum);
        }
    }
    let mut minimax = (0, f64::INFINITY);
    for col in 0..cols {
        let maximum = (0..rows)
            .map(|row| matrix[row * cols + col])
            .fold(f64::NEG_INFINITY, f64::max);
        if maximum < minimax.1 {
            minimax = (col, maximum);
        }
    }
    (minimax.1 - maximin.1 <= TOLERANCE).then_some((maximin.0, minimax.0))
}

/// Le meilleur gain des lignes contre `col_strategy`, et le gain que `row_strategy` garantit contre toute colonne : à
/// l'équilibre, ils sont égaux, et égaux à la valeur du jeu.
fn replies(matrix: &[f64], cols: usize, row_strategy: &[f64], col_strategy: &[f64]) -> (f64, f64) {
    let best_row_reply = (0..row_strategy.len())
        .map(|row| {
            (0..cols)
                .map(|col| matrix[row * cols + col] * col_strategy[col])
                .sum::<f64>()
        })
        .fold(f64::NEG_INFINITY, f64::max);
    let worst_col_reply = (0..cols)
        .map(|col| {
            (0..row_strategy.len())
                .map(|row| row_strategy[row] * matrix[row * cols + col])
                .sum::<f64>()
        })
        .fold(f64::INFINITY, f64::min);
    (best_row_reply, worst_col_reply)
}

fn normalize(strategy: &mut [f64]) {
    let total: f64 = strategy.iter().sum();
    for probability in strategy {
        *probability /= total;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `docs/IA.md` § 4.4 : un pierre-feuille-ciseaux à quatre mises, 25 % sur chaque mise pour les deux joueurs,
    /// valeur −0,5, et chaque colonne rapporte −0,5 contre la stratégie des lignes.
    #[test]
    fn l_exemple_de_reference_d_ia_md() {
        let matrix = [
            -2.0, -1.0, 0.0, 1.0, 1.0, -2.0, -1.0, 0.0, 0.0, 1.0, -2.0, -1.0, -1.0, 0.0, 1.0, -2.0,
        ];
        let mut solver = Solver::new();
        let solution = solver.solve(&matrix, 4, 4);
        assert!(!solution.pure);
        assert!((solution.value + 0.5).abs() < TOLERANCE);
        for probability in solution.rows.iter().chain(solution.cols) {
            assert!((probability - 0.25).abs() < TOLERANCE);
        }
        for col in 0..4 {
            let payoff: f64 = (0..4).map(|row| solution.rows[row] * matrix[row * 4 + col]).sum();
            assert!((payoff + 0.5).abs() < TOLERANCE);
        }
    }

    #[test]
    fn un_point_selle_donne_une_solution_pure() {
        // la ligne 1 garantit 0,4 ; la colonne 0 ne cède pas plus de 0,4
        let matrix = [0.3, 0.9, 0.4, 0.6, 0.2, 0.8];
        let mut solver = Solver::new();
        let solution = solver.solve(&matrix, 3, 2);
        assert!(solution.pure);
        assert_eq!(solution.value, 0.4);
        assert_eq!(solution.rows, [0.0, 1.0, 0.0]);
        assert_eq!(solution.cols, [1.0, 0.0]);
    }

    #[test]
    fn une_seule_ligne_ou_une_seule_colonne() {
        let mut solver = Solver::new();
        assert_eq!(solver.solve(&[0.7], 1, 1).value, 0.7);
        assert_eq!(solver.solve(&[0.7, 0.2, 0.9], 1, 3).value, 0.2); // les colonnes choisissent le minimum
        assert_eq!(solver.solve(&[0.7, 0.2, 0.9], 3, 1).value, 0.9); // les lignes choisissent le maximum
    }

    #[test]
    fn un_solveur_se_reutilise_pour_des_matrices_de_tailles_differentes() {
        let mut solver = Solver::new();
        let pierre_feuille_ciseaux = [0.5, 0.0, 1.0, 1.0, 0.5, 0.0, 0.0, 1.0, 0.5];
        assert!((solver.solve(&pierre_feuille_ciseaux, 3, 3).value - 0.5).abs() < TOLERANCE);
        assert_eq!(solver.solve(&[0.1, 0.8], 2, 1).value, 0.8);
        assert!((solver.solve(&pierre_feuille_ciseaux, 3, 3).value - 0.5).abs() < TOLERANCE);
    }
}
