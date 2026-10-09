//! Niveau 4 : effets persistants, transcrit de `apply_capacity_lvl_4.py`.

use super::{bit, Round, ENEMY, SIDES};
use crate::contract::{Effect, PlayerState};
use crate::vocabulary::{effect_kinds, types};

const LIFE: u32 = bit(types::LIFE);
const PILLZ: u32 = bit(types::PILLZ);

/// Attributs touchés par chaque sorte (`_STATS_OF_KIND`), en masque sur TYPES : repair verse la vie et les pillz,
/// combust prend les deux.
const fn stats_of_kind(kind: u8) -> u32 {
    match kind {
        effect_kinds::DOPE | effect_kinds::CONSUME => PILLZ,
        effect_kinds::REPAIR | effect_kinds::COMBUST => LIFE | PILLZ,
        _ => LIFE,
    }
}

/// Poison, toxine, consume, combust : des pertes (`_LOSS_KINDS`), que l'adversaire pose (`_CAUSED_BY_OPPONENT`).
const fn is_loss(kind: u8) -> bool {
    matches!(
        kind,
        effect_kinds::POISON | effect_kinds::TOXINE | effect_kinds::CONSUME | effect_kinds::COMBUST
    )
}

impl Round<'_> {
    pub(super) fn apply_capacity_lvl_4(&mut self) {
        for side in SIDES {
            let opp = ENEMY - side;
            let effects = self.players[side];
            // gains d'abord (combat réel 1735837), chacun dans l'ordre d'activation : le tri stable de Python
            for losses in [false, true] {
                for effect in effects.effects().iter().filter(|effect| is_loss(effect.kind) == losses) {
                    let author = if is_loss(effect.kind) { opp } else { side };
                    let suspended = stats_of_kind(effect.kind) & self.fighters[author].cancelled;
                    if suspended != stats_of_kind(effect.kind) {
                        apply_tick(&mut self.players[side], effect, suspended);
                    }
                }
            }
        }
    }
}

/// Applique l'effet à chacun de ses attributs, sauf ceux suspendus ce round par un Annul.
fn apply_tick(player: &mut PlayerState, effect: &Effect, suspended: u32) {
    let unbounded = effect.borne == -1;
    for stat in [LIFE, PILLZ] {
        if stats_of_kind(effect.kind) & stat == 0 || suspended & stat != 0 {
            continue;
        }
        let current = if stat == LIFE {
            &mut player.life
        } else {
            &mut player.pillz
        };
        if is_loss(effect.kind) {
            let floor = if unbounded { 0 } else { effect.borne };
            if *current > floor {
                *current = floor.max(*current - effect.value);
            }
        } else if unbounded {
            *current += effect.value;
        } else if *current < effect.borne {
            *current = effect.borne.min(*current + effect.value);
        }
    }
}
