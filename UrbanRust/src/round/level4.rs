//! Niveau 4 : effets persistants, transcrit de `apply_capacity_lvl_4.py`. À la fin d'un round où les deux joueurs
//! sont en vie :
//!   1. les effets déjà actifs agissent, les gains avant les pertes (combat réel 1735837) ;
//!   2. les capacités persistantes restantes (leur condition de fin de round a été validée au niveau 3) sont posées
//!      sur le joueur visé, multiplicateur résolu à l'activation ; un effet remplace celui de même sorte, une toxine
//!      remplace aussi le poison du joueur visé et une regen son heal, avant que l'effet remplacé n'agisse ;
//!   3. toxine, regen, dope, repair et consume agissent dès le round où ils sont posés, combust seulement posé par
//!      un Mindwipe (how « immediate »).

use super::{affected_sides, bit, Round, ENEMY, LIFE, PILLZ, SIDES, SLOTS};
use crate::contract::{CompiledCapacity, Effect, PlayerState};
use crate::vocabulary::{effect_kinds, hows, types};

/// Les types persistants et la sorte d'effet qu'ils posent, **dans l'ordre de TYPES** : une capacité qui en porte
/// plusieurs pose la première dans cet ordre, comme le Python, qui relit ses types depuis le masque.
const PERSISTENT_TYPES: [(u8, u8); 8] = [
    (types::COMBUST, effect_kinds::COMBUST),
    (types::CONSUME, effect_kinds::CONSUME),
    (types::DOPE, effect_kinds::DOPE),
    (types::HEAL, effect_kinds::HEAL),
    (types::POISON, effect_kinds::POISON),
    (types::REGEN, effect_kinds::REGEN),
    (types::REPAIR, effect_kinds::REPAIR),
    (types::TOXINE, effect_kinds::TOXINE),
];
const _: () = {
    let mut index = 1;
    while index < PERSISTENT_TYPES.len() {
        assert!(
            PERSISTENT_TYPES[index - 1].0 < PERSISTENT_TYPES[index].0,
            "PERSISTENT_TYPES hors de l'ordre de TYPES"
        );
        index += 1;
    }
};

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

/// Les sortes qui agissent dès le round où elles sont posées (glossaire officiel 51, 52 ; repair : utilisateur).
const fn is_immediate(kind: u8) -> bool {
    matches!(
        kind,
        effect_kinds::TOXINE | effect_kinds::REGEN | effect_kinds::DOPE | effect_kinds::REPAIR | effect_kinds::CONSUME
    )
}

impl Round<'_> {
    pub(super) fn apply_capacity_lvl_4(&mut self) {
        self.drop_effects_replaced_before_acting();
        for side in SIDES {
            let opp = ENEMY - side;
            let effects = self.players[side];
            // gains d'abord, chacun dans l'ordre d'activation : le tri stable de Python
            for losses in [false, true] {
                for effect in effects.effects().iter().filter(|effect| is_loss(effect.kind) == losses) {
                    // un Annul suspend les effets posés par la carte qu'il vise (glossaire 56)
                    let author = if is_loss(effect.kind) { opp } else { side };
                    let suspended = stats_of_kind(effect.kind) & self.fighters[author].cancelled;
                    if suspended != stats_of_kind(effect.kind) {
                        apply_tick(&mut self.players[side], effect, suspended);
                    }
                }
            }
        }
        for side in SIDES {
            for slot in SLOTS {
                if let Some(capacity) = self.fighters[side].slots[slot].take() {
                    self.register_capacity(side, &capacity);
                }
            }
        }
    }

    /// Pose l'effet d'une capacité persistante sur chaque joueur visé, et le fait agir aussitôt s'il est immédiat.
    fn register_capacity(&mut self, side: usize, capacity: &CompiledCapacity) {
        let Some(kind) = persistent_kind(capacity) else {
            return;
        };
        let value = capacity.value * self.multiplier(capacity.how, side);
        let suspended = stats_of_kind(kind) & self.fighters[side].cancelled;
        let immediate = is_immediate(kind) || capacity.how == hows::IMMEDIATE;
        for affected in affected_sides(capacity.target, side) {
            let effect = Effect { kind, value, borne: capacity.borne };
            self.players[affected].register(effect);
            if immediate && suspended != stats_of_kind(kind) {
                apply_tick(&mut self.players[affected], &effect, suspended);
            }
        }
    }

    /// Une toxine posée ce round remplace le poison du joueur visé, une regen son heal, avant que l'effet remplacé
    /// agisse (combats réels 1647870, 1734431).
    fn drop_effects_replaced_before_acting(&mut self) {
        for side in SIDES {
            for slot in SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                // la première dans l'ordre de TYPES : regen avant toxine
                let replaced = if capacity.types & bit(types::REGEN) != 0 {
                    effect_kinds::HEAL
                } else if capacity.types & bit(types::TOXINE) != 0 {
                    effect_kinds::POISON
                } else {
                    continue;
                };
                for affected in affected_sides(capacity.target, side) {
                    self.players[affected].remove(replaced);
                }
            }
        }
    }
}

fn persistent_kind(capacity: &CompiledCapacity) -> Option<u8> {
    PERSISTENT_TYPES
        .iter()
        .find(|(type_index, _)| capacity.types & bit(*type_index) != 0)
        .map(|&(_, kind)| kind)
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
