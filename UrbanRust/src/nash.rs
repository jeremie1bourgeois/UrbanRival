//! Le solveur de jeux matriciels à somme nulle : la valeur et un équilibre de Nash d'une matrice dont les lignes sont
//! le joueur qui maximise (`docs/IA.md` § 4.3). Écrit pour les matrices du moteur, petites (au plus ~23 × 92) : la
//! solution pure d'abord (un point-selle, fréquent au round 4), sinon le simplexe. Chaque solution est vérifiée par
//! son écart à l'équilibre. Pour les datasets, `Solver::equilibria` donne en plus, pour chaque coup, l'équilibre qui le
//! joue le plus. SciPy ne sert qu'aux tests (`tests/nash.rs`).

/// Écart à l'équilibre toléré : les valeurs du jeu sont des probabilités, dans [0, 1].
pub const TOLERANCE: f64 = 1e-9;
/// En deçà, un coefficient du tableau du simplexe compte pour nul.
const PIVOT_EPSILON: f64 = 1e-11;
/// Au-delà, un coût réduit à l'optimum est strictement positif : sa variable reste nulle dans tout équilibre.
const POSITIVE_REDUCED_COST: f64 = 1e-9;

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

/// Pour chaque coup de chaque joueur, une stratégie optimale qui le joue avec la plus forte probabilité possible.
///
/// Les équilibres d'un jeu à somme nulle forment un produit : toute stratégie optimale des lignes, avec toute
/// stratégie optimale des colonnes, est un équilibre. L'ensemble des stratégies optimales des lignes est exactement
/// {p ≥ 0, Σ p = 1, pᵀ M ≥ valeur} : la matrice et sa valeur le décrivent entier. `row_strategy(i)[i]` est donc la plus
/// forte probabilité que la ligne i reçoive dans un équilibre ; 0 : elle n'est jouée dans aucun.
pub struct Equilibria<'a> {
    pub value: f64,
    /// Une stratégie optimale de chaque joueur, celle que trouve le simplexe.
    pub rows: &'a [f64],
    pub cols: &'a [f64],
    row_strategies: &'a [f64],
    col_strategies: &'a [f64],
}

impl<'a> Equilibria<'a> {
    /// La stratégie optimale des lignes qui joue la ligne `row` le plus.
    pub fn row_strategy(&self, row: usize) -> &'a [f64] {
        let rows = self.rows.len();
        &self.row_strategies[row * rows..(row + 1) * rows]
    }

    /// La stratégie optimale des colonnes qui joue la colonne `col` le plus.
    pub fn col_strategy(&self, col: usize) -> &'a [f64] {
        let cols = self.cols.len();
        &self.col_strategies[col * cols..(col + 1) * cols]
    }
}

/// Les tampons du solveur, dimensionnés au premier appel puis réutilisés : rien n'est alloué ensuite pour des matrices
/// de même taille ou plus petites.
#[derive(Default)]
pub struct Solver {
    rows: Vec<f64>,
    cols: Vec<f64>,
    tableau: Tableau,
    // pour `equilibria`
    optimum: Tableau,
    banned: Vec<bool>,
    row_strategies: Vec<f64>,
    col_strategies: Vec<f64>,
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
                self.tableau.load(rows, cols, |row, col| matrix[row * cols + col]);
                self.tableau.optimize(|_| true);
                self.tableau.row_strategy(&mut self.rows);
                self.tableau.col_strategy(&mut self.cols);
                (self.tableau.value(), false)
            }
        };
        let gap = verify(matrix, cols, &self.rows, &self.cols, value);
        Solution { value, rows: &self.rows, cols: &self.cols, pure, gap }
    }

    /// Pour chaque coup de chaque joueur, la stratégie optimale qui le joue le plus (`Equilibria`). Chaque stratégie
    /// rendue est vérifiée, avec la stratégie optimale trouvée pour l'autre joueur.
    pub fn equilibria(&mut self, matrix: &[f64], rows: usize, cols: usize) -> Equilibria<'_> {
        assert!(
            rows > 0 && cols > 0 && matrix.len() == rows * cols,
            "matrice {rows} × {cols} mal formée"
        );
        self.rows.resize(rows, 0.0);
        self.cols.resize(cols, 0.0);
        self.row_strategies.resize(rows * rows, 0.0);
        self.col_strategies.resize(cols * cols, 0.0);

        self.tableau.load(rows, cols, |row, col| matrix[row * cols + col]);
        self.tableau.optimize(|_| true);
        let value = self.tableau.value();
        self.tableau.row_strategy(&mut self.rows);
        self.tableau.col_strategy(&mut self.cols);
        self.best_strategies(false);
        // les lignes de M sont les colonnes du jeu vu par les colonnes, −Mᵀ
        self.tableau.load(cols, rows, |row, col| -matrix[col * cols + row]);
        self.tableau.optimize(|_| true);
        self.best_strategies(true);

        for row in 0..rows {
            verify(
                matrix,
                cols,
                &self.row_strategies[row * rows..(row + 1) * rows],
                &self.cols,
                value,
            );
        }
        for col in 0..cols {
            verify(
                matrix,
                cols,
                &self.rows,
                &self.col_strategies[col * cols..(col + 1) * cols],
                value,
            );
        }
        Equilibria {
            value,
            rows: &self.rows,
            cols: &self.cols,
            row_strategies: &self.row_strategies,
            col_strategies: &self.col_strategies,
        }
    }

    /// Depuis le tableau à l'optimum, pour chaque colonne de son jeu, la stratégie des colonnes optimale qui la joue
    /// le plus : dans `row_strategies` si ce jeu est −Mᵀ (`rows_of_matrix`), sinon dans `col_strategies`.
    ///
    /// Une stratégie est optimale si et seulement si les variables de coût réduit strictement positif à l'optimum y
    /// restent nulles (complémentarité avec les variables duales trouvées, même si l'optimum est dégénéré). On repart
    /// donc du tableau optimal, ces variables interdites, pour maximiser la variable du coup : quelques pivots.
    fn best_strategies(&mut self, rows_of_matrix: bool) {
        let Self { tableau, optimum, banned, row_strategies, col_strategies, .. } = self;
        let strategies = if rows_of_matrix { row_strategies } else { col_strategies };
        let actions = tableau.cols;
        optimum.copy_from(tableau);
        banned.clear();
        banned.extend((0..optimum.rhs()).map(|variable| optimum.objective[variable] > POSITIVE_REDUCED_COST));
        for action in 0..actions {
            let strategy = &mut strategies[action * actions..(action + 1) * actions];
            if banned[action] {
                optimum.col_strategy(strategy); // ce coup n'est joué dans aucun équilibre
                continue;
            }
            tableau.copy_from(optimum);
            tableau.maximize(action);
            tableau.optimize(|variable| !banned[variable]);
            tableau.col_strategy(strategy);
        }
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

    /// Le jeu `rows × cols` dont `entry` donne les valeurs, décalé, à l'objectif Σ y, la base étant celle des écarts.
    fn load(&mut self, rows: usize, cols: usize, entry: impl Fn(usize, usize) -> f64) {
        self.rows = rows;
        self.cols = cols;
        let minimum = (0..rows)
            .flat_map(|row| (0..cols).map(move |col| (row, col)))
            .map(|(row, col)| entry(row, col))
            .fold(f64::INFINITY, f64::min);
        self.shift = 1.0 - minimum;
        let (width, rhs) = (self.width(), self.rhs());
        self.cells.clear();
        self.cells.resize(rows * width, 0.0);
        for row in 0..rows {
            for col in 0..cols {
                self.cells[row * width + col] = entry(row, col) + self.shift;
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

    /// Recopie `other` dans les tampons de ce tableau, sans réallouer.
    fn copy_from(&mut self, other: &Tableau) {
        self.rows = other.rows;
        self.cols = other.cols;
        self.shift = other.shift;
        self.cells.clone_from(&other.cells);
        self.objective.clone_from(&other.objective);
        self.basis.clone_from(&other.basis);
    }

    /// L'objectif devient « maximiser la variable `variable` », exprimé dans la base courante : ses coûts réduits, et
    /// sa valeur courante dans la dernière case.
    fn maximize(&mut self, variable: usize) {
        let width = self.width();
        self.objective.fill(0.0);
        self.objective[variable] = -1.0;
        if let Some(row) = self.basis.iter().position(|&basic| basic == variable) {
            for col in 0..width {
                self.objective[col] += self.cells[row * width + col];
            }
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

    /// La plus forte probabilité de chaque ligne et de chaque colonne dans un équilibre.
    fn best_probabilities(matrix: &[f64], rows: usize, cols: usize) -> (Vec<f64>, Vec<f64>) {
        let mut solver = Solver::new();
        let equilibria = solver.equilibria(matrix, rows, cols);
        let row_best = (0..rows).map(|row| equilibria.row_strategy(row)[row]).collect();
        let col_best = (0..cols).map(|col| equilibria.col_strategy(col)[col]).collect();
        (row_best, col_best)
    }

    fn assert_close(found: &[f64], expected: &[f64]) {
        assert_eq!(found.len(), expected.len());
        for (found, expected) in found.iter().zip(expected) {
            assert!((found - expected).abs() < TOLERANCE, "{found} au lieu de {expected}");
        }
    }

    #[test]
    fn un_coup_en_double_partage_sa_probabilite_avec_son_double() {
        // pierre-feuille-ciseaux, la pierre en deux exemplaires : à eux deux, un tiers ; chacun peut le prendre seul
        let matrix = [0.5, 0.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 0.0, 0.0, 1.0, 0.5];
        let (rows, cols) = best_probabilities(&matrix, 4, 3);
        assert_close(&rows, &[1.0 / 3.0; 4]);
        assert_close(&cols, &[1.0 / 3.0; 3]);
    }

    #[test]
    fn dans_une_matrice_constante_tout_coup_peut_etre_joue_seul() {
        let (rows, cols) = best_probabilities(&[0.5; 6], 2, 3);
        assert_close(&rows, &[1.0; 2]);
        assert_close(&cols, &[1.0; 3]);
    }

    #[test]
    fn une_ligne_strictement_dominee_n_est_jamais_jouee() {
        // la ligne 2 rapporte 0,4 quoi qu'il arrive, sous la valeur 0,5
        let (rows, cols) = best_probabilities(&[1.0, 0.0, 0.0, 1.0, 0.4, 0.4], 3, 2);
        assert_close(&rows, &[0.5, 0.5, 0.0]);
        assert_close(&cols, &[0.5, 0.5]);
    }

    #[test]
    fn une_ligne_faiblement_dominee_peut_etre_jouee_seule() {
        // la ligne 2 rapporte la valeur 0,5 quoi qu'il arrive : la jouer toujours est optimal
        let (rows, cols) = best_probabilities(&[1.0, 0.0, 0.0, 1.0, 0.5, 0.5], 3, 2);
        assert_close(&rows, &[0.5, 0.5, 1.0]);
        assert_close(&cols, &[0.5, 0.5]);
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
