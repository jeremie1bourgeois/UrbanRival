//! Niveau 3 : effets de fin de round sur la vie et les pillz des joueurs, une fois les deux joueurs encore en vie (les
//! KO sont traités avant, par `apply_reanimate`) ; transcrit de `apply_capacity_lvl_3.py`. Chaque capacité restante
//! est filtrée par sa condition de fin de round (Defeat, Backlash, Victory or Defeat, ou victoire implicite sans
//! condition), puis appliquée une seule fois ; ce qui n'est ni vie ni pillz reste pour le niveau 4.

use std::cmp::Reverse;

use super::{affected_sides, bit, Fighter, Round, ENEMY, FURY_COST, LIFE, PILLZ, SIDES, SLOTS};
use crate::contract::CompiledCapacity;
use crate::vocabulary::{conditions, targets, types};

impl Round<'_> {
    /// Les gains passent avant les pertes, quelle que soit la carte qui les porte : un plancher mord après le gain
    /// adverse (combats réels 1734030, 1734587). Entre deux pertes, le plancher le plus haut d'abord, comme au niveau
    /// 2, quelle que soit la carte qui le porte (décision utilisateur, 2026-10-09).
    pub(super) fn apply_capacity_lvl_3(&mut self) {
        // plus aucune capacité sur les deux cartes, le cas d'une case sur deux : rien à appliquer (README, « Optimisations
        // en place »)
        if self.carried_capacities().next().is_none() {
            return;
        }
        for losses in [false, true] {
            // les emplacements de la passe, dans l'ordre des camps : (camp, emplacement, plancher)
            let mut pending = [(0, 0, 0); SIDES.len() * SLOTS.len()];
            let mut count = 0;
            for side in SIDES {
                for slot in SLOTS {
                    if let Some(capacity) = self.fighters[side].slots[slot] {
                        if is_loss(&capacity) == losses {
                            pending[count] = (side, slot, capacity.borne);
                            count += 1;
                        }
                    }
                }
            }
            if losses {
                // tri stable : à plancher égal, deux pertes commutent
                pending[..count].sort_by_key(|&(_, _, floor)| Reverse(floor));
            }
            for &(side, slot, _) in &pending[..count] {
                let capacity = self.fighters[side].slots[slot].expect("un emplacement relevé plein");
                self.fighters[side].slots[slot] = self.apply_end_of_round(side, capacity);
            }
        }
    }

    fn apply_end_of_round(&mut self, side: usize, capacity: CompiledCapacity) -> Option<CompiledCapacity> {
        let opp = ENEMY - side;
        let won = self.fighters[side].win;
        // Reanimate = « Defeat: +X Life » (le cas KO est traité par apply_reanimate)
        if has_type(&capacity, types::REANIMATE) {
            if !won {
                self.players[side].life += capacity.value * self.multiplier(capacity.how, side);
            }
            return None;
        }
        let capacity = check_capacity_condition_lvl_3(capacity, won)?;
        if has_type(&capacity, types::KO) {
            self.players[opp].life = 0; // Fatal Killshot / Sinister Symmetry : KO immédiat
            return None;
        }
        if has_type(&capacity, types::RECOVER) {
            self.players[side].pillz += recovered_pillz(&self.fighters[side], &capacity);
            if capacity.target == targets::BOTH {
                // « Recover X Players Pillz » : chacun sur sa propre mise
                self.players[opp].pillz += recovered_pillz(&self.fighters[opp], &capacity);
            }
            return None;
        }
        let stats = capacity.types & (LIFE | PILLZ);
        if stats == 0 {
            return Some(capacity);
        }
        let bonus = capacity.value * self.multiplier(capacity.how, side);
        for affected in affected_sides(capacity.target, side) {
            let player = &mut self.players[affected];
            if stats & LIFE != 0 {
                apply_to(&mut player.life, bonus, capacity.borne);
            }
            if stats & PILLZ != 0 {
                apply_to(&mut player.pillz, bonus, capacity.borne);
            }
        }
        None
    }

    /// Reanimate : le joueur tombé à 0 vie récupère X vies si la carte qu'il vient de jouer porte l'effet.
    pub(super) fn apply_reanimate(&mut self) {
        for side in SIDES {
            if self.players[side].life > 0 {
                continue;
            }
            for slot in SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                if has_type(&capacity, types::REANIMATE) {
                    self.players[side].life += capacity.value * self.multiplier(capacity.how, side);
                    self.fighters[side].slots[slot] = None;
                }
            }
        }
    }
}

fn has_type(capacity: &CompiledCapacity, type_index: u8) -> bool {
    capacity.types & bit(type_index) != 0
}

fn is_loss(capacity: &CompiledCapacity) -> bool {
    capacity.value < 0 || has_type(capacity, types::KO)
}

/// Filtre la capacité selon l'issue du round : sans condition, seulement en cas de victoire ; Backlash, en cas de
/// victoire, se retourne contre son porteur.
fn check_capacity_condition_lvl_3(mut capacity: CompiledCapacity, won: bool) -> Option<CompiledCapacity> {
    let has = |condition: u8| capacity.conditions & bit(condition) != 0;
    let applies = if capacity.conditions == 0 {
        won
    } else if has(conditions::BACKLASH) {
        capacity.target = targets::ALLY;
        won
    } else if has(conditions::DEFEAT) {
        !won
    } else if has(conditions::VICTORY_DEFEAT) {
        true
    } else {
        panic!("condition de fin de round inattendue : {:#b}", capacity.conditions)
    };
    capacity.conditions = 0;
    applies.then_some(capacity)
}

/// « Recover X Pillz Out Of Y » : pillz posées × X / Y arrondi en dessous, au moins 1 ; la fury compte.
fn recovered_pillz(fighter: &Fighter, capacity: &CompiledCapacity) -> i16 {
    if capacity.borne <= 0 {
        return 0;
    }
    let placed = fighter.pillz + if fighter.fury { FURY_COST } else { 0 };
    (placed * capacity.value).div_euclid(capacity.borne).max(1)
}

/// Contrairement au niveau 2, le sens de la borne se lit sur le gain multiplié, pas sur la valeur imprimée.
fn apply_to(current: &mut i16, bonus: i16, borne: i16) {
    if borne != -1 {
        if bonus > 0 && *current < borne {
            *current = borne.min(*current + bonus);
        } else if bonus < 0 && *current > borne {
            *current = borne.max(*current + bonus);
        }
    } else {
        *current += bonus;
    }
}
