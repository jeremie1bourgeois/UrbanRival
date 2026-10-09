//! La recherche exacte : la valeur d'un état selon `docs/IA.md` § 5.1, avec une mémo.
//!
//! V(état) vaut 1 / 0,5 / 0 si la partie est finie. Sinon, le premier joueur F choisit sa carte (publique), puis F mise
//! et S choisit carte et mise sans voir la mise de F : pour chaque carte de F, un jeu matriciel — lignes = mises de F,
//! colonnes = (carte, mise) de S dans l'ordre des coups légaux, cases = V de l'état suivant pour F — ; F prend la carte
//! de meilleure valeur. V est rendue pour l'allié. Les matrices se remplissent par blocs de mises (une carte de F
//! contre une carte de S) ; la référence est `scripts/build_search_expected.py`, en Python (`tests/recherche.rs`).
//!
//! `Search::parallel` répartit sur les cœurs les états suivants des premiers rounds. La valeur d'un état se calcule
//! toujours de la même façon, quel que soit le fil : les deux modes donnent les mêmes nombres, au bit près.
//!
//! Les contrôles : chaque matrice est vérifiée par le solveur, toujours ; en mode test (assertions de debug, actives
//! sous `cargo test`), chaque valeur est une probabilité, dans [0, 1] ; `Search::mirror_mismatches` vérifie que chaque
//! état résolu, vu de l'autre camp, vaut 1 − V.

use std::cell::RefCell;
use std::collections::HashMap;
use std::hash::{BuildHasher, BuildHasherDefault, Hasher};
use std::sync::RwLock;

use rayon::prelude::*;

use crate::contract::{Deck, State, HAND_SIZE};
use crate::game::{card_actions, terminal};
use crate::nash::{Solver, TOLERANCE};
use crate::round::play_block;

/// Jusqu'à ce round compris, `Search::parallel` répartit les états suivants d'un état sur les cœurs ; au-delà, ils
/// sont trop vite résolus pour que la répartition rapporte.
const PARALLEL_UNTIL_ROUND: u8 = 3;
/// Morceaux de la mémo : assez pour que deux fils veuillent rarement le même au même instant.
const MEMO_SHARDS: usize = 64;

thread_local! {
    // un solveur par fil : ses tampons servent à toutes les matrices que le fil résout
    static SOLVER: RefCell<Solver> = RefCell::new(Solver::new());
}

/// La recherche sur un deck : la mémo garde la valeur de chaque état déjà résolu.
pub struct Search<'a> {
    deck: &'a Deck,
    memo: Memo,
    parallel: bool,
}

impl<'a> Search<'a> {
    /// Une recherche sur un seul fil.
    pub fn new(deck: &'a Deck) -> Self {
        Search { deck, memo: Memo::new(), parallel: false }
    }

    /// Une recherche qui répartit son travail sur tous les cœurs.
    pub fn parallel(deck: &'a Deck) -> Self {
        Search { deck, memo: Memo::new(), parallel: true }
    }

    /// V(état) pour l'allié.
    pub fn value(&self, state: &State) -> f64 {
        if let Some(end) = terminal(state) {
            return end;
        }
        if let Some(known) = self.memo.get(state) {
            return known;
        }
        let best = self
            .card_values(state)
            .into_iter()
            .flatten()
            .fold(f64::NEG_INFINITY, f64::max);
        let value = if state.ally_first { best } else { 1.0 - best };
        self.memo.insert(*state, value);
        value
    }

    /// Pour chaque carte de la main du premier joueur, la valeur pour lui de son jeu de mises ; None si jouée.
    ///
    /// En trois temps : les états suivants de tous les blocs (carte de F, puis carte de S, puis case du bloc), leurs
    /// valeurs, puis les matrices.
    pub fn card_values(&self, state: &State) -> [Option<f64>; HAND_SIZE] {
        let ally_first = state.ally_first;
        let (first, second) = if ally_first {
            (&state.ally, &state.enemy)
        } else {
            (&state.enemy, &state.ally)
        };
        let first_cards: Vec<usize> = (0..HAND_SIZE).filter(|&card| !first.has_played(card)).collect();
        let reply_cards: Vec<usize> = (0..HAND_SIZE).filter(|&card| !second.has_played(card)).collect();

        let mut next_states = Vec::new();
        for &card in &first_cards {
            for &reply_card in &reply_cards {
                let (ally_card, enemy_card) = if ally_first {
                    (card, reply_card)
                } else {
                    (reply_card, card)
                };
                play_block(self.deck, state, ally_card, enemy_card, |_, _, next_state, _| {
                    next_states.push(*next_state)
                });
            }
        }
        let next_values: Vec<f64> = if self.parallel && state.nb_turn <= PARALLEL_UNTIL_ROUND {
            next_states
                .par_iter()
                .map(|next_state| self.value(next_state))
                .collect()
        } else {
            next_states.iter().map(|next_state| self.value(next_state)).collect()
        };

        let cols: usize = reply_cards.iter().map(|&card| card_actions(second, card).count()).sum();
        let mut values = [None; HAND_SIZE];
        let mut next = next_values.iter();
        for &card in &first_cards {
            let rows = card_actions(first, card).count();
            let mut matrix = vec![0.0; rows * cols];
            let mut col_offset = 0;
            for &reply_card in &reply_cards {
                let bets = card_actions(second, reply_card).count();
                // le bloc va ligne par ligne, lignes = mises de l'allié : transposé quand F est l'ennemi
                let enemy_bets = if ally_first { bets } else { rows };
                for index in 0..rows * bets {
                    let (ally_bet, enemy_bet) = (index / enemy_bets, index % enemy_bets);
                    let (row, bet) = if ally_first {
                        (ally_bet, enemy_bet)
                    } else {
                        (enemy_bet, ally_bet)
                    };
                    let value = *next.next().expect("une valeur par état suivant");
                    matrix[row * cols + col_offset + bet] = if ally_first { value } else { 1.0 - value };
                }
                col_offset += bets;
            }
            let value = SOLVER.with(|solver| solver.borrow_mut().solve(&matrix, rows, cols).value);
            debug_assert!(
                (-TOLERANCE..=1.0 + TOLERANCE).contains(&value),
                "valeur {value} hors de [0, 1] : {state:?}"
            );
            values[card] = Some(value);
        }
        values
    }

    /// Le nombre d'états non terminaux résolus et gardés en mémo.
    pub fn solved_states(&self) -> usize {
        self.memo.len()
    }

    /// La place que les tables de la mémo réservent à leurs entrées, en octets, remplies ou non ; chaque table y ajoute
    /// un peu (un octet de contrôle par case, des cases en réserve) : c'est un minimum.
    pub fn memo_bytes(&self) -> usize {
        self.memo.bytes()
    }

    /// Les états non terminaux résolus, chacun avec sa valeur pour l'allié, dans un ordre quelconque.
    pub fn solved(&self) -> Vec<(State, f64)> {
        self.memo.entries()
    }

    /// Contrôle : vu de l'autre camp, chaque état résolu vaut 1 − V. `mirror` est une recherche sur `Deck::mirrored`,
    /// qui résout le miroir de chaque état (`State::mirrored`) ; rend les états qui s'en écartent de plus de
    /// `TOLERANCE`, avec leur valeur et celle de leur miroir. On compare des valeurs, pas des ensembles d'états : la
    /// seule asymétrie connue du round (`KNOWN_ASYMMETRIES`, l'ordre d'enregistrement des effets persistants) mène
    /// parfois le miroir à un état aux mêmes effets dans un autre ordre, sans en changer la valeur jusqu'ici.
    pub fn mirror_mismatches(&self, mirror: &Search) -> Vec<(State, f64, f64)> {
        self.solved()
            .into_iter()
            .filter_map(|(state, value)| {
                let mirrored = mirror.value(&state.mirrored());
                ((mirrored - (1.0 - value)).abs() > TOLERANCE).then_some((state, value, mirrored))
            })
            .collect()
    }
}

/// La mémo, partagée entre les fils : des tables indépendantes, choisies par l'empreinte de l'état, chacune sous son
/// verrou. Deux fils qui résolvent le même état en même temps trouvent la même valeur : seul le travail est doublé.
/// Un verrou lecteurs-rédacteur : les consultations, presque toutes réussies (99 % pour les états du round 4 d'une
/// partie entière), passent ensemble ; seule l'écriture d'un état résolu attend (README, « Optimisations en place »).
struct Memo {
    shards: Vec<RwLock<MemoTable>>,
}

type MemoTable = HashMap<State, f64, BuildHasherDefault<StateHasher>>;

impl Memo {
    fn new() -> Self {
        Memo {
            shards: (0..MEMO_SHARDS).map(|_| RwLock::new(MemoTable::default())).collect(),
        }
    }

    /// Le morceau se choisit sur les bits 48 à 53 de l'empreinte, que la table n'utilise pas : elle place l'état par
    /// les bits du bas et le reconnaît par les 7 du haut. Choisi sur les bits du bas, chaque morceau n'en remplirait
    /// qu'une case sur 64.
    fn shard(&self, state: &State) -> &RwLock<MemoTable> {
        let hash = BuildHasherDefault::<StateHasher>::default().hash_one(state);
        &self.shards[(hash >> 48) as usize % MEMO_SHARDS]
    }

    fn get(&self, state: &State) -> Option<f64> {
        self.shard(state).read().unwrap().get(state).copied()
    }

    fn insert(&self, state: State, value: f64) {
        self.shard(&state).write().unwrap().insert(state, value);
    }

    fn len(&self) -> usize {
        self.shards.iter().map(|shard| shard.read().unwrap().len()).sum()
    }

    fn bytes(&self) -> usize {
        let entry = std::mem::size_of::<(State, f64)>();
        self.shards
            .iter()
            .map(|shard| shard.read().unwrap().capacity() * entry)
            .sum()
    }

    fn entries(&self) -> Vec<(State, f64)> {
        self.shards
            .iter()
            .flat_map(|shard| {
                shard
                    .read()
                    .unwrap()
                    .iter()
                    .map(|(&state, &value)| (state, value))
                    .collect::<Vec<_>>()
            })
            .collect()
    }
}

/// Le hachage de la mémo : chaque mot de l'état (`impl Hash for State`, quelques mots de 64 bits) mêlé par une
/// multiplication, comme FxHash, puis le finaliseur de MurmurHash3, qui répartit chaque bit d'entrée sur tous ceux de
/// l'empreinte. Quelques nanosecondes par état contre ~12 pour SipHash, dont la mémo n'a pas besoin : ses clés ne
/// viennent pas d'un adversaire (README, « Optimisations en place »).
#[derive(Default)]
struct StateHasher {
    hash: u64,
}

impl Hasher for StateHasher {
    fn write_u64(&mut self, word: u64) {
        self.hash = (self.hash.rotate_left(5) ^ word).wrapping_mul(0x517c_c1b7_2722_0a95);
    }

    fn write(&mut self, bytes: &[u8]) {
        for chunk in bytes.chunks(8) {
            let mut word = [0; 8];
            word[..chunk.len()].copy_from_slice(chunk);
            self.write_u64(u64::from_le_bytes(word));
        }
    }

    fn finish(&self) -> u64 {
        let mut hash = self.hash;
        hash ^= hash >> 33;
        hash = hash.wrapping_mul(0xff51_afd7_ed55_8ccd);
        hash ^= hash >> 33;
        hash = hash.wrapping_mul(0xc4ce_b9fe_1a85_ec53);
        hash ^ hash >> 33
    }
}
