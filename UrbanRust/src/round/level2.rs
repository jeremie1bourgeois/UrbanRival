//! Niveau 2 : modificateurs de puissance, dégâts et attaque des cartes en combat, transcrit de
//! `apply_capacity_lvl_2.py`. Appelé en deux passes : puissance et dégâts avant le calcul de l'attaque, attaque après.

use super::{affected_sides, Round, ABILITY, ATTACK, BONUS, DAMAGE, LEADER, POWER, SIDES};
use crate::contract::CompiledCapacity;
use crate::vocabulary::targets;

/// À plancher égal : carte alliée puis ennemie, et bonus, pouvoir, Leader (`_MODIFIER_SLOTS`).
const MODIFIER_SLOTS: [usize; 3] = [BONUS, ABILITY, LEADER];

impl Round<'_> {
    /// Applique les modificateurs des stats `stats` : cible ally, puis both, puis enemy, plancher le plus haut d'abord.
    pub(super) fn apply_capacity_lvl_2(&mut self, stats: u32) {
        // aucune capacité ne touche ces stats : chacune serait rendue telle quelle (la passe de l'attaque, à chaque case
        // d'un bloc, le plus souvent ; README, « Optimisations en place »)
        if !self.carried_capacities().any(|capacity| capacity.types & stats != 0) {
            return;
        }
        for target in [targets::ALLY, targets::BOTH, targets::ENEMY] {
            let (modifiers, count) = self.modifiers_highest_floor_first();
            for &(side, slot) in &modifiers[..count] {
                if let Some(capacity) = self.fighters[side].slots[slot] {
                    self.fighters[side].slots[slot] = self.apply_targeted(target, side, capacity, stats);
                }
            }
        }
    }

    /// (camp, emplacement) des capacités des deux cartes, plancher le plus haut d'abord ; le tri reste stable
    /// (REGLES 3.6 bis : la réduction au plancher le plus haut s'applique d'abord, quelle que soit la carte).
    fn modifiers_highest_floor_first(&self) -> ([(usize, usize); 6], usize) {
        let mut modifiers = [(0, 0); 6];
        let mut count = 0;
        let borne = |(side, slot): (usize, usize)| self.fighters[side].slots[slot].map_or(0, |capacity| capacity.borne);
        for side in SIDES {
            for slot in MODIFIER_SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                let mut position = count;
                while position > 0 && borne(modifiers[position - 1]) < capacity.borne {
                    modifiers[position] = modifiers[position - 1];
                    position -= 1;
                }
                modifiers[position] = (side, slot);
                count += 1;
            }
        }
        (modifiers, count)
    }

    /// Applique la capacité si sa cible est `target` ; consommée (None) quand ses types de niveau 2 sont épuisés.
    fn apply_targeted(
        &mut self,
        target: u8,
        side: usize,
        mut capacity: CompiledCapacity,
        stats: u32,
    ) -> Option<CompiledCapacity> {
        let applied = capacity.types & stats;
        if capacity.target != target || applied == 0 {
            return Some(capacity);
        }
        let bonus = capacity.value * self.multiplier(capacity.how, side);
        for card_side in affected_sides(target, side) {
            let fighter = &mut self.fighters[card_side];
            for stat in [POWER, DAMAGE, ATTACK] {
                if applied & stat != 0 {
                    apply_to(fighter.stat_mut(stat), bonus, capacity.borne, capacity.value > 0);
                }
            }
        }
        capacity.types &= !applied;
        (capacity.types != 0).then_some(capacity)
    }
}

/// Une borne n'est franchie que dans le sens de la capacité : un « Max » ne fait pas baisser, un « Min » pas monter.
fn apply_to(current: &mut i16, bonus: i16, borne: i16, increase: bool) {
    if borne != -1 {
        if increase && *current < borne {
            *current = borne.min(*current + bonus);
        } else if !increase && *current > borne {
            *current = borne.max(*current + bonus);
        }
    } else {
        *current += bonus;
    }
}
