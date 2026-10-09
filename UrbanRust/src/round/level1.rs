//! Niveau 1 : capacités « méta », qui agissent sur les autres capacités ou sur les valeurs imprimées, avant tout
//! modificateur de stats ; transcrit de `apply_capacity_lvl_1.py`. Quatre phases, puis les capacités méta sont
//! consommées :
//!   1. Copy: Opp. Ability / Bonus (`apply_copies`, appelé par `process_round` entre les deux passes de conditions) ;
//!   2. Protection: Ability / Bonus et Stop Opp. Ability / Bonus, résolus « en chaîne » ;
//!   3. Copy / Exchange / Impose de puissance et dégâts, sur les valeurs imprimées ;
//!   4. Cancel Opp. X Modif. et Protection: X.

use super::{printed, Round, ABILITY, ATTACK, BONUS, DAMAGE, ENEMY, LIFE, PILLZ, POWER, SIDES, SLOTS};
use crate::contract::CompiledCapacity;
use crate::vocabulary::{conditions, hows, targets, types};

/// Les emplacements qu'une capacité méta peut viser ; leur indice est celui de l'emplacement de même nom.
const KINDS: [usize; 2] = [ABILITY, BONUS];

impl Round<'_> {
    pub(super) fn apply_capacity_lvl_1(&mut self) {
        self.apply_stops();
        self.apply_value_copies_and_exchanges();
        self.apply_cancels();
        self.apply_stat_protections();
        self.consume_meta_capacities();
    }

    // --- Phase 1 : Copy: Opp. Ability / Bonus -------------------------------------------------

    /// `sources` : les emplacements des deux cartes **avant** l'évaluation des conditions de début de round, pour que
    /// la copie garde ses conditions et qu'elles soient réévaluées pour le copieur. Les deux copies sont simultanées.
    pub(super) fn apply_copies(&mut self, sources: &[[Option<CompiledCapacity>; 3]; 2]) {
        let mut planned = [[None; 2]; 2]; // [camp][emplacement] : Some(copie) si l'emplacement copie
        for side in SIDES {
            for slot in KINDS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                if capacity.how != hows::COPY {
                    continue;
                }
                let Some(kind) = kind_targeted(&capacity) else {
                    continue;
                };
                let source = sources[ENEMY - side][kind];
                // une copie d'emplacement ne se copie pas
                planned[side][slot] = Some(source.filter(|source| !is_slot_copy(source)));
            }
        }
        for side in SIDES {
            for slot in KINDS {
                if let Some(copied) = planned[side][slot] {
                    self.fighters[side].slots[slot] = copied;
                }
            }
        }
    }

    // --- Phase 2 : Protection: Ability / Bonus et Stop Opp. Ability / Bonus -------------------

    /// Emplacements stoppés, [camp][emplacement], résolus « en chaîne » (support UR, art. 91) : un Stop stoppé ne
    /// stoppe rien, une Protection stoppée ne protège rien. Point fixe sur les emplacements sûrement actifs / sûrement
    /// stoppés ; ce qui reste indéterminé (cycle, ex. SoA contre SoA) est stoppé : les Stops gagnent. Une décision
    /// prise ne change plus et les deux règles s'excluent : le résultat ne dépend pas de l'ordre de visite.
    fn stopped_slots(&self) -> [[bool; 2]; 2] {
        #[derive(Clone, Copy, PartialEq)]
        enum Status {
            Unknown,
            Active,
            Stopped,
        }
        let mut status = [[Status::Unknown; 2]; 2];
        loop {
            let mut changed = false;
            for side in SIDES {
                for kind in KINDS {
                    if status[side][kind] != Status::Unknown {
                        continue;
                    }
                    let opp = ENEMY - side;
                    // un Stop ou une Protection a l'état de l'emplacement qui le porte
                    let attackers = || {
                        self.slots_targeting(opp, hows::STOP, kind)
                            .map(|slot| status[opp][slot])
                    };
                    let shields = || {
                        self.slots_targeting(side, hows::PROTECTION, kind)
                            .map(|slot| status[side][slot])
                    };
                    let decided = if attackers().all(|state| state == Status::Stopped)
                        || shields().any(|state| state == Status::Active)
                    {
                        Status::Active
                    } else if attackers().any(|state| state == Status::Active)
                        && shields().all(|state| state == Status::Stopped)
                    {
                        Status::Stopped
                    } else {
                        continue;
                    };
                    status[side][kind] = decided;
                    changed = true;
                }
            }
            if !changed {
                return status.map(|kinds| kinds.map(|state| state != Status::Active));
            }
        }
    }

    /// Emplacements (pouvoir, bonus) de `side` qui portent une capacité méta `how` visant l'emplacement `kind`.
    fn slots_targeting(&self, side: usize, how: u8, kind: usize) -> impl Iterator<Item = usize> + '_ {
        KINDS.into_iter().filter(move |&slot| {
            self.fighters[side].slots[slot]
                .is_some_and(|capacity| capacity.how == how && kind_targeted(&capacity) == Some(kind))
        })
    }

    /// Un emplacement stoppé perd sa capacité, sauf un « Stop: X », qui s'active justement parce qu'on le stoppe ;
    /// un « Stop: X » qu'on ne stoppe pas reste inerte.
    fn apply_stops(&mut self) {
        let stopped = self.stopped_slots();
        for side in SIDES {
            for slot in KINDS {
                let Some(mut capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                let activated_by_stop = capacity.conditions & super::bit(conditions::STOP) != 0;
                capacity.conditions &= !super::bit(conditions::STOP);
                let kept = stopped[side][slot] == activated_by_stop;
                self.fighters[side].slots[slot] = kept.then_some(capacity);
            }
        }
    }

    // --- Phase 3 : Copy / Exchange / Impose de puissance et dégâts ----------------------------

    fn apply_value_copies_and_exchanges(&mut self) {
        for side in SIDES {
            let opp = ENEMY - side;
            for slot in SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                if !matches!(capacity.how, hows::COPY | hows::EXCHANGE | hows::IMPOSE) {
                    continue;
                }
                for stat in [POWER, DAMAGE] {
                    // le Cancel adverse annule l'Exchange (combat réel 1294992), l'Impose (1412809) et la Copie (1734264)
                    if capacity.types & stat == 0 || self.cancels_stat(opp, stat) {
                        continue;
                    }
                    let (own_printed, opp_printed) = (printed(self.card(side), stat), printed(self.card(opp), stat));
                    if capacity.how == hows::IMPOSE {
                        *self.fighters[opp].stat_mut(stat) = own_printed; // l'adversaire prend ma valeur imprimée
                        continue;
                    }
                    *self.fighters[side].stat_mut(stat) = opp_printed;
                    if capacity.how == hows::EXCHANGE {
                        *self.fighters[opp].stat_mut(stat) = own_printed;
                    }
                }
            }
        }
    }

    /// `side` porte-t-il un « Cancel Opp. <stat> Modif. » actif (les Stops ont déjà retiré ceux stoppés) ?
    fn cancels_stat(&self, side: usize, stat: u32) -> bool {
        self.fighters[side].slots.iter().flatten().any(|capacity| {
            capacity.how == hows::CANCEL && capacity.types & stat != 0 && capacity.target != targets::ALLY
        })
    }

    // --- Phase 4 : Cancel Opp. X Modif. et Protection: X --------------------------------------

    /// Retire `stripped` des capacités d'effet de `side` ; une capacité sans type restant disparaît.
    ///
    /// `only_targeting_opponent` (Protection) : un « Cards », qui frappe les deux cartes, ne disparaît pas — il se
    /// replie sur son porteur, qui continue de se réduire lui-même (combat réel 1412809).
    fn strip_types(&mut self, side: usize, stripped: u32, only_targeting_opponent: bool) {
        for slot in &mut self.fighters[side].slots {
            let Some(capacity) = slot else {
                continue;
            };
            if is_meta(capacity.how) {
                continue;
            }
            if only_targeting_opponent && capacity.target != targets::ENEMY {
                if capacity.target == targets::BOTH && capacity.types & stripped != 0 {
                    capacity.target = targets::ALLY;
                }
                continue;
            }
            capacity.types &= !stripped;
            if capacity.types == 0 {
                *slot = None;
            }
        }
    }

    /// Un Cancel retire ses stats des modifications adverses, quelle que soit leur cible ; Life / Pillz suspendent
    /// aussi les effets persistants adverses pour le round (glossaire officiel 56). « Cancel Players X Mod. »
    /// (Leaders) agit des deux côtés.
    fn apply_cancels(&mut self) {
        for side in SIDES {
            for slot in SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                if capacity.how != hows::CANCEL {
                    continue;
                }
                self.cancel_modifications(ENEMY - side, capacity.types);
                if capacity.target == targets::BOTH {
                    self.cancel_modifications(side, capacity.types);
                }
            }
        }
    }

    fn cancel_modifications(&mut self, side: usize, cancelled: u32) {
        self.strip_types(side, cancelled, false);
        self.fighters[side].cancelled |= cancelled & (LIFE | PILLZ);
    }

    /// Protection: X retire X des modifications adverses qui ciblent ma carte ; « Cards » protège les deux cartes.
    fn apply_stat_protections(&mut self) {
        for side in SIDES {
            for slot in SLOTS {
                let Some(capacity) = self.fighters[side].slots[slot] else {
                    continue;
                };
                let protected = capacity.types & (POWER | DAMAGE | ATTACK);
                if capacity.how != hows::PROTECTION || protected == 0 {
                    continue;
                }
                self.strip_types(ENEMY - side, protected, true);
                if capacity.target == targets::BOTH {
                    self.strip_types(side, protected, true);
                }
            }
        }
    }

    // --- Consommation -------------------------------------------------------------------------

    /// Tune Out et Tie-break survivent : `process_round` les lit plus tard.
    fn consume_meta_capacities(&mut self) {
        for fighter in &mut self.fighters {
            for slot in &mut fighter.slots {
                if slot.is_some_and(|capacity| {
                    is_meta(capacity.how) && !matches!(capacity.how, hows::TUNE_OUT | hows::TIE_BREAK)
                }) {
                    *slot = None;
                }
            }
        }
    }
}

/// `META_HOWS` : les capacités qui agissent sur les autres plutôt que sur les stats.
fn is_meta(how: u8) -> bool {
    matches!(
        how,
        hows::STOP
            | hows::COPY
            | hows::PROTECTION
            | hows::CANCEL
            | hows::EXCHANGE
            | hows::IMPOSE
            | hows::TUNE_OUT
            | hows::TIE_BREAK
    )
}

/// L'emplacement visé par une capacité méta (pouvoir, sinon bonus), ou None si elle vise une stat (Copy: Opp. Power).
fn kind_targeted(capacity: &CompiledCapacity) -> Option<usize> {
    if capacity.types & super::bit(types::ABILITY) != 0 {
        Some(ABILITY)
    } else if capacity.types & super::bit(types::BONUS) != 0 {
        Some(BONUS)
    } else {
        None
    }
}

fn is_slot_copy(capacity: &CompiledCapacity) -> bool {
    capacity.how == hows::COPY && kind_targeted(capacity).is_some()
}
