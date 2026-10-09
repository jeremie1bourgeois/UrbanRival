//! Le solveur de jeux matriciels à somme nulle : la valeur et un équilibre de Nash d'une matrice dont les lignes sont
//! le joueur qui maximise (`docs/IA.md` § 4.3). Écrit pour les matrices du moteur, petites (au plus ~23 × 92) : la
//! solution pure d'abord (un point-selle, fréquent au round 4), sinon le simplexe. Chaque solution est vérifiée par
//! son écart à l'équilibre. Pour les datasets, `Solver::equilibria` donne en plus, pour chaque coup, l'équilibre qui le
//! joue le plus, et `Solver::corners` tous les coins de l'ensemble des équilibres. SciPy ne sert qu'aux tests
//! (`tests/nash.rs`).

use std::collections::{HashSet, VecDeque};

/// Écart à l'équilibre toléré : les valeurs du jeu sont des probabilités, dans [0, 1].
pub const TOLERANCE: f64 = 1e-9;
/// En deçà, un coefficient du tableau du simplexe compte pour nul.
const PIVOT_EPSILON: f64 = 1e-11;
/// Au-delà, un coût réduit à l'optimum est strictement positif : sa variable reste nulle dans tout équilibre.
const POSITIVE_REDUCED_COST: f64 = 1e-9;
/// Plafond du nombre de coins par joueur : au-delà, la liste est rendue tronquée, et signalée comme telle.
pub const MAX_CORNERS: usize = 256;
/// Plafond du nombre de bases visitées par joueur (un coin dégénéré en a plusieurs) : le travail reste borné.
const MAX_BASES: usize = 10_000;

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

/// Les coins de l'ensemble des stratégies optimales de chaque joueur. Cet ensemble est un polytope : toute stratégie
/// optimale est un mélange de ses coins, et tout mélange de coins est optimal. Une liste peut être tronquée au plafond
/// (`MAX_CORNERS`, ou trop de bases visitées) : `rows_complete` et `cols_complete` le disent.
pub struct Corners {
    pub value: f64,
    pub rows: Vec<Vec<f64>>,
    pub cols: Vec<Vec<f64>>,
    pub rows_complete: bool,
    pub cols_complete: bool,
}

/// Les tampons du solveur, dimensionnés au premier appel puis réutilisés : rien n'est alloué ensuite pour des matrices
/// de même taille ou plus petites.
#[derive(Default)]
pub struct Solver {
    rows: Vec<f64>,
    cols: Vec<f64>,
    tableau: Tableau,
    // pour `equilibria` et `corners`
    optimum: Tableau,
    initial: Tableau,
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
    /// le plus : dans `row_strategies` si ce jeu est −Mᵀ (`rows_of_matrix`), sinon dans `col_strategies`. On repart du
    /// tableau optimal, les variables hors de la face optimale interdites, pour maximiser la variable du coup :
    /// quelques pivots.
    fn best_strategies(&mut self, rows_of_matrix: bool) {
        let Self { tableau, optimum, banned, row_strategies, col_strategies, .. } = self;
        let strategies = if rows_of_matrix { row_strategies } else { col_strategies };
        let actions = tableau.cols;
        optimum.copy_from(tableau);
        optimum.optimal_face(banned);
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

    /// Les coins de l'ensemble des stratégies optimales de chaque joueur (`Corners`), au plus `MAX_CORNERS` chacun.
    /// Chaque coin rendu est vérifié, avec la stratégie optimale trouvée pour l'autre joueur.
    pub fn corners(&mut self, matrix: &[f64], rows: usize, cols: usize) -> Corners {
        assert!(
            rows > 0 && cols > 0 && matrix.len() == rows * cols,
            "matrice {rows} × {cols} mal formée"
        );
        self.rows.resize(rows, 0.0);
        self.cols.resize(cols, 0.0);

        self.initial.load(rows, cols, |row, col| matrix[row * cols + col]);
        self.tableau.copy_from(&self.initial);
        self.tableau.optimize(|_| true);
        let value = self.tableau.value();
        self.tableau.row_strategy(&mut self.rows);
        self.tableau.col_strategy(&mut self.cols);
        let (col_corners, cols_complete) = self.optimal_corners();
        // les lignes de M sont les colonnes du jeu vu par les colonnes, −Mᵀ
        self.initial.load(cols, rows, |row, col| -matrix[col * cols + row]);
        self.tableau.copy_from(&self.initial);
        self.tableau.optimize(|_| true);
        let (row_corners, rows_complete) = self.optimal_corners();

        for corner in &row_corners {
            verify(matrix, cols, corner, &self.cols, value);
        }
        for corner in &col_corners {
            verify(matrix, cols, &self.rows, corner, value);
        }
        Corners {
            value,
            rows: row_corners,
            cols: col_corners,
            rows_complete,
            cols_complete,
        }
    }

    /// Les coins de la face optimale du tableau à l'optimum (des stratégies des colonnes de son jeu), en visitant ses
    /// bases de proche en proche depuis la base trouvée ; faux si un plafond a été atteint.
    ///
    /// Grâce au départage lexicographique, les bases de la face optimale sont les sommets d'un polytope perturbé non
    /// dégénéré : son graphe est connexe, et chaque coin de la face est l'image d'au moins un de ses sommets. Les
    /// voisines d'une base s'obtiennent en faisant entrer une variable autorisée ; chaque base est recalculée depuis le
    /// tableau initial (`initial`, base des écarts).
    fn optimal_corners(&mut self) -> (Vec<Vec<f64>>, bool) {
        let Self { tableau, initial, banned, .. } = self;
        tableau.optimal_face(banned);
        let start = tableau.basis.clone();
        let mut visited = HashSet::from([sorted(&start)]);
        let mut queue = VecDeque::from([start]);
        let mut corners: Vec<Vec<f64>> = Vec::new();
        while let Some(basis) = queue.pop_front() {
            tableau.rebuild(initial, &basis);
            let mut corner = vec![0.0; tableau.cols];
            tableau.col_strategy(&mut corner);
            if !corners.iter().any(|known| same_strategy(known, &corner)) {
                if corners.len() == MAX_CORNERS {
                    return (corners, false);
                }
                corners.push(corner);
            }
            for (entering, &outside_face) in banned.iter().enumerate() {
                if outside_face || tableau.basis.contains(&entering) {
                    continue;
                }
                let Some(leaving) = tableau.leaving_row(entering) else {
                    continue;
                };
                let mut neighbor = tableau.basis.clone();
                neighbor[leaving] = entering;
                if visited.insert(sorted(&neighbor)) {
                    if visited.len() > MAX_BASES {
                        return (corners, false);
                    }
                    queue.push_back(neighbor);
                }
            }
        }
        (corners, true)
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

    /// Le simplexe jusqu'à l'optimum de l'objectif courant, en ne faisant entrer que les variables `allowed` : entre la
    /// première variable de coût réduit négatif, sort la ligne que choisit `leaving_row`.
    fn optimize(&mut self, allowed: impl Fn(usize) -> bool) {
        let rhs = self.rhs();
        while let Some(entering) = (0..rhs).find(|&col| self.objective[col] < -PIVOT_EPSILON && allowed(col)) {
            let leaving = self
                .leaving_row(entering)
                .expect("simplexe non borné : impossible sur un jeu décalé à valeurs positives");
            self.pivot(leaving, entering);
        }
    }

    /// La ligne qui sort quand `entering` entre : celle du plus petit rapport, les égalités départagées dans l'ordre
    /// lexicographique des lignes de B⁻¹ (les colonnes des écarts) divisées par le pivot. Ce départage revient à
    /// perturber infinitésimalement le second membre : plus aucune base n'est dégénérée, le simplexe ne peut pas
    /// cycler, et chaque base est un sommet distinct du problème perturbé (ce qu'exige `corners`). None : rien ne
    /// borne la variable.
    fn leaving_row(&self, entering: usize) -> Option<usize> {
        let width = self.width();
        let mut leaving: Option<usize> = None;
        for row in 0..self.rows {
            if self.cells[row * width + entering] <= PIVOT_EPSILON {
                continue;
            }
            if leaving.is_none_or(|best| self.lexicographically_smaller(row, best, entering)) {
                leaving = Some(row);
            }
        }
        leaving
    }

    /// La ligne `row`, divisée par son coefficient dans `entering`, précède-t-elle `other` sur (second membre, B⁻¹) ?
    fn lexicographically_smaller(&self, row: usize, other: usize, entering: usize) -> bool {
        let width = self.width();
        let (pivot, other_pivot) = (self.cells[row * width + entering], self.cells[other * width + entering]);
        for col in std::iter::once(self.rhs()).chain(self.cols..self.cols + self.rows) {
            let (value, other_value) = (
                self.cells[row * width + col] / pivot,
                self.cells[other * width + col] / other_pivot,
            );
            if value < other_value - PIVOT_EPSILON {
                return true;
            }
            if value > other_value + PIVOT_EPSILON {
                return false;
            }
        }
        false
    }

    /// Interdit, dans `banned`, les variables de coût réduit strictement positif à l'optimum : une stratégie est
    /// optimale si et seulement si ces variables y restent nulles (complémentarité avec les variables duales trouvées,
    /// même si l'optimum est dégénéré). Le reste est la face optimale.
    fn optimal_face(&self, banned: &mut Vec<bool>) {
        banned.clear();
        banned.extend((0..self.rhs()).map(|variable| self.objective[variable] > POSITIVE_REDUCED_COST));
    }

    /// Le tableau de la base `basis`, recalculé depuis le tableau initial `initial` (base des écarts) plutôt
    /// qu'atteint de pivot en pivot depuis une autre base : les erreurs d'arrondi ne s'accumulent pas.
    fn rebuild(&mut self, initial: &Tableau, basis: &[usize]) {
        self.copy_from(initial);
        let width = self.width();
        for &variable in basis {
            if self.basis.contains(&variable) {
                continue;
            }
            // parmi les lignes dont la variable doit sortir, celle du plus grand coefficient (pivot partiel)
            let magnitude = |row: usize| self.cells[row * width + variable].abs();
            let row = (0..self.rows)
                .filter(|&row| !basis.contains(&self.basis[row]))
                .max_by(|&row, &other| magnitude(row).total_cmp(&magnitude(other)))
                .expect("base de taille incohérente");
            assert!(magnitude(row) > PIVOT_EPSILON, "base singulière");
            self.pivot(row, variable);
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

fn sorted(basis: &[usize]) -> Vec<usize> {
    let mut key = basis.to_vec();
    key.sort_unstable();
    key
}

fn same_strategy(strategy: &[f64], other: &[f64]) -> bool {
    strategy
        .iter()
        .zip(other)
        .all(|(probability, other)| (probability - other).abs() <= TOLERANCE)
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

    /// Les coins de chaque joueur, triés ; les deux listes doivent être complètes.
    fn corners_of(matrix: &[f64], rows: usize, cols: usize) -> (Vec<Vec<f64>>, Vec<Vec<f64>>) {
        let mut corners = Solver::new().corners(matrix, rows, cols);
        assert!(corners.rows_complete && corners.cols_complete);
        corners.rows.sort_by(|corner, other| corner.partial_cmp(other).unwrap());
        corners.cols.sort_by(|corner, other| corner.partial_cmp(other).unwrap());
        (corners.rows, corners.cols)
    }

    fn assert_corners(found: &[Vec<f64>], expected: &[&[f64]]) {
        assert_eq!(found.len(), expected.len(), "{found:?} au lieu de {expected:?}");
        for (found, expected) in found.iter().zip(expected) {
            assert_close(found, expected);
        }
    }

    #[test]
    fn deux_exemplaires_d_un_coup_donnent_deux_coins() {
        // pierre-feuille-ciseaux, la pierre en deux exemplaires : le tiers de la pierre sur l'un ou sur l'autre
        let matrix = [0.5, 0.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 0.0, 0.0, 1.0, 0.5];
        let (rows, cols) = corners_of(&matrix, 4, 3);
        let third = 1.0 / 3.0;
        assert_corners(&rows, &[&[0.0, third, third, third], &[third, 0.0, third, third]]);
        assert_corners(&cols, &[&[third, third, third]]);
    }

    #[test]
    fn les_coins_d_une_matrice_constante_sont_les_coups_purs() {
        let (rows, cols) = corners_of(&[0.5; 6], 2, 3);
        assert_corners(&rows, &[&[0.0, 1.0], &[1.0, 0.0]]);
        assert_corners(&cols, &[&[0.0, 0.0, 1.0], &[0.0, 1.0, 0.0], &[1.0, 0.0, 0.0]]);
    }

    #[test]
    fn une_ligne_faiblement_dominee_est_un_coin_a_elle_seule() {
        let (rows, cols) = corners_of(&[1.0, 0.0, 0.0, 1.0, 0.5, 0.5], 3, 2);
        assert_corners(&rows, &[&[0.0, 0.0, 1.0], &[0.5, 0.5, 0.0]]);
        assert_corners(&cols, &[&[0.5, 0.5]]);
    }

    #[test]
    fn une_ligne_strictement_dominee_n_entre_dans_aucun_coin() {
        let (rows, cols) = corners_of(&[1.0, 0.0, 0.0, 1.0, 0.4, 0.4], 3, 2);
        assert_corners(&rows, &[&[0.5, 0.5, 0.0]]);
        assert_corners(&cols, &[&[0.5, 0.5]]);
    }

    #[test]
    fn le_plafond_de_coins_est_signale() {
        // une seule colonne, toutes les lignes égales : chaque ligne pure est un coin, un de plus que le plafond
        let corners = Solver::new().corners(&[0.5; MAX_CORNERS + 1], MAX_CORNERS + 1, 1);
        assert!(!corners.rows_complete);
        assert_eq!(corners.rows.len(), MAX_CORNERS);
        assert!(corners.cols_complete);
        assert_eq!(corners.cols.len(), 1);
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
