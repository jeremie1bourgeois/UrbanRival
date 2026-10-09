//! Niveau 1 : capacités « méta », qui agissent sur les autres capacités ou sur les valeurs imprimées, transcrit de
//! `apply_capacity_lvl_1.py`. Après leurs phases, les capacités méta sont consommées.

use super::{Round, SIDES, SLOTS};
use crate::vocabulary::hows;

impl Round<'_> {
    pub(super) fn apply_capacity_lvl_1(&mut self) {
        self.consume_meta_capacities();
    }

    /// Tune Out et Tie-break survivent : `process_round` les lit plus tard.
    fn consume_meta_capacities(&mut self) {
        for side in SIDES {
            for slot in SLOTS {
                if self.fighters[side].slots[slot].is_some_and(|capacity| is_consumed_meta(capacity.how)) {
                    self.fighters[side].slots[slot] = None;
                }
            }
        }
    }
}

/// Les `META_HOWS`, hors Tune Out et Tie-break.
fn is_consumed_meta(how: u8) -> bool {
    matches!(
        how,
        hows::STOP | hows::COPY | hows::PROTECTION | hows::CANCEL | hows::EXCHANGE | hows::IMPOSE
    )
}
