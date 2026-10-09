//! Clan d'une carte en main, transcrit de `clan.py` : son propre clan, ou celui qu'un Oculus « Infiltrated » adopte.

use super::bit;
use crate::contract::{CompiledCard, HAND_SIZE};
use crate::vocabulary::{clans, conditions, types};

pub(super) fn is_infiltrated(card: &CompiledCard) -> bool {
    card.clan == clans::OCULUS
        && card
            .bonus
            .is_some_and(|bonus| bonus.types & bit(types::INFILTRATED) != 0)
}

/// Clan adopté par l'Oculus « Infiltrated » de la main : un seul autre clan -> celui-là ; deux autres clans -> celui
/// de la carte seule ; trois autres clans ou plus d'un Oculus -> aucun. Chaque Leader est son propre clan
/// (`_clan_for_infiltration`) : deux Leaders différents font deux clans, deux exemplaires du même n'en font qu'un.
pub(super) fn infiltrated_clan(hand: &[CompiledCard]) -> Option<u8> {
    if hand.iter().filter(|card| card.clan == clans::OCULUS).count() != 1 {
        return None;
    }
    let mut groups = [((0, 0), 0); HAND_SIZE]; // ((clan, personnage pour un Leader), nombre de cartes)
    let mut group_count = 0;
    for card in hand.iter().filter(|card| card.clan != clans::OCULUS) {
        let key = (
            card.clan,
            if card.clan == clans::LEADER {
                card.character
            } else {
                u8::MAX
            },
        );
        match groups[..group_count].iter_mut().find(|(group, _)| *group == key) {
            Some((_, count)) => *count += 1,
            None => {
                groups[group_count] = (key, 1);
                group_count += 1;
            }
        }
    }
    let groups = &groups[..group_count];
    let chosen = match groups.len() {
        1 => Some(groups[0].0),
        2 => {
            let mut lone = groups.iter().filter(|(_, count)| *count == 1);
            match (lone.next(), lone.next()) {
                (Some((key, _)), None) => Some(*key),
                _ => None,
            }
        }
        _ => None,
    };
    chosen.map(|(clan, _)| clan)
}

/// Clans listés sur la carte Oculus (condition « infiltrated » de son pouvoir), en masque ; None si inconnus.
pub(super) fn infiltrable_clans(card: &CompiledCard) -> Option<u64> {
    card.ability
        .filter(|ability| ability.conditions & bit(conditions::INFILTRATED) != 0)
        .map(|ability| ability.clans)
}

/// Clan dont la carte porte le bonus : son propre clan, ou le clan adopté pour un Oculus infiltré.
pub(super) fn clan_for_bonus(hand: &[CompiledCard], index: usize) -> Option<u8> {
    if is_infiltrated(&hand[index]) {
        infiltrated_clan(hand)
    } else {
        Some(hand[index].clan)
    }
}

/// Le bonus de clan s'active si la main compte au moins 2 personnages distincts du clan (`is_clan_bonus_active`).
pub(super) fn is_clan_bonus_active(hand: &[CompiledCard], index: usize) -> bool {
    let Some(clan) = clan_for_bonus(hand, index) else {
        return false;
    };
    let mut characters = 0u8;
    for mate in 0..hand.len() {
        if clan_for_bonus(hand, mate) == Some(clan) {
            characters |= 1 << hand[mate].character;
        }
    }
    characters.count_ones() >= 2
}

/// Cartes de la main du même clan que la carte (pour Support et Brawl) : un Oculus rallié compte, les doublons aussi.
pub(super) fn clan_mates(hand: &[CompiledCard], index: usize) -> i16 {
    let clan = clan_for_bonus(hand, index);
    (0..hand.len())
        .filter(|&mate| clan_for_bonus(hand, mate) == clan)
        .count() as i16
}
