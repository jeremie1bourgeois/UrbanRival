//! Multiplicateurs de capacités (champ `how`), transcrits de `multipliers.py` : le facteur appliqué à `value`, vu
//! du camp qui porte la capacité.

use super::{clan, hand, Round, ALLY, ENEMY};
use crate::vocabulary::hows;

impl Round<'_> {
    pub(super) fn multiplier(&self, how: u8, side: usize) -> i16 {
        let opp = ENEMY - side;
        let player = &self.players[side];
        let (start_life, start_pillz) = if side == ALLY {
            self.deck.ally_start
        } else {
            self.deck.enemy_start
        };
        match how {
            hows::NONE | hows::IMMEDIATE => 1,
            hows::GROWTH => self.nb_turn as i16,
            hows::DEGROWTH => 5 - self.nb_turn as i16,
            hows::SUPPORT => clan::clan_mates(hand(self.deck, side), self.fighters[side].index),
            hows::EQUALIZER => self.card(opp).stars as i16,
            hows::BRAWL => clan::clan_mates(hand(self.deck, opp), self.fighters[opp].index),
            hows::NB_DAM_OPP => self.card(opp).damage,
            // dégâts de la carte après modificateurs, qu'elle gagne ou perde
            hows::NB_DAMAGE => self.fighters[side].damage,
            hows::NB_POW_OPP => self.card(opp).power,
            hows::NB_LIFE_LOST => (start_life - player.life).max(0),
            hows::NB_PILLZ_LOST => (start_pillz - self.pillz_left(side)).max(0),
            hows::NB_PILLZ_LEFT => self.pillz_left(side),
            hows::NB_LIFE_LEFT => player.life,
            _ => panic!("how sans multiplicateur : {how}"),
        }
    }

    /// Pillz restantes avant la mise du round, pillz gratuite non comprise : la mise est déjà prélevée.
    fn pillz_left(&self, side: usize) -> i16 {
        let fighter = &self.fighters[side];
        self.players[side].pillz + (fighter.pillz - 1) + if fighter.fury { super::FURY_COST } else { 0 }
    }
}
