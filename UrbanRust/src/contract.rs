//! L'état compact d'une partie, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py`.
//!
//! Deux moitiés, comme côté Python : le **deck**, immuable pendant la partie, et l'**état**, qui change à chaque
//! round. Tout est de taille fixe et `Copy` — aucun tas, aucune indirection : l'IA copie, hache et compare des états
//! par millions, c'est le seul endroit où la représentation décide de la vitesse.
//!
//! Deux bornes justifient les tableaux fixes :
//!   - une main fait exactement 4 cartes (validé par `game_schemas.py`) ;
//!   - un joueur porte au plus 8 effets persistants, un par sorte : `register_persistent_effect` remplace l'effet
//!     de même sorte au lieu de l'empiler.

use crate::vocabulary::EFFECT_KINDS;

pub const HAND_SIZE: usize = 4;
pub const MAX_EFFECTS: usize = EFFECT_KINDS.len();

/// Capacité compilée : plus un mot, rien que des indices dans le vocabulaire et des masques de bits.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct CompiledCapacity {
    pub how: u8,    // indice dans HOWS
    pub target: u8, // indice dans TARGETS
    pub types: u32, // masque de bits sur TYPES
    pub value: i16,
    pub borne: i16,      // -1 = sans borne
    pub conditions: u32, // masque de bits sur CONDITIONS
    pub bet_over: u8,    // « Bet > N » : N, si le bit « bet » est levé et bet_under vaut 0
    pub bet_under: u8,   // « Bet < N » : N (jamais 0 : une mise n'est pas négative)
    pub clans: u64,      // masque de bits sur CLANS de la condition versus / after / infiltrated
}

/// Carte compilée. Le nom n'y est pas : il sert à lire un corpus, jamais à jouer un round.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct CompiledCard {
    pub stars: u8,
    pub clan: u8, // indice dans CLANS
    pub power: i16,
    pub damage: i16,
    pub ability: Option<CompiledCapacity>,
    pub bonus: Option<CompiledCapacity>,
}

/// Les huit cartes de la partie et la situation de départ de chaque camp, lue par « Par Vie / Pillz perdue ».
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Deck {
    pub ally: [CompiledCard; HAND_SIZE],
    pub enemy: [CompiledCard; HAND_SIZE],
    pub ally_start: (i16, i16), // vie, pillz
    pub enemy_start: (i16, i16),
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Effect {
    pub kind: u8, // indice dans EFFECT_KINDS
    pub value: i16,
    pub borne: i16, // -1 = sans borne
}

impl Effect {
    /// Case vide d'un tableau d'effets : `kind` hors vocabulaire, pour que deux états égaux se hachent pareil.
    const EMPTY: Effect = Effect { kind: u8::MAX, value: 0, borne: 0 };
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct PlayerState {
    pub life: i16,
    pub pillz: i16,
    pub played: u8, // bit i levé = la carte i de la main a déjà été jouée
    effect_count: u8,
    effects: [Effect; MAX_EFFECTS], // dans l'ordre d'activation : le niveau 4 les applique dans cet ordre
}

impl PlayerState {
    pub fn new(life: i16, pillz: i16, played: u8) -> Self {
        PlayerState {
            life,
            pillz,
            played,
            effect_count: 0,
            effects: [Effect::EMPTY; MAX_EFFECTS],
        }
    }

    pub fn has_played(&self, card: usize) -> bool {
        self.played >> card & 1 == 1
    }

    pub fn set_played(&mut self, card: usize) {
        self.played |= 1 << card;
    }

    pub fn effects(&self) -> &[Effect] {
        &self.effects[..self.effect_count as usize]
    }

    /// Enregistre l'effet en remplaçant celui de même sorte s'il existe, qui perd sa place dans l'ordre
    /// d'activation (`register_persistent_effect`, côté Python).
    pub fn register(&mut self, effect: Effect) {
        let mut kept = 0;
        for index in 0..self.effect_count as usize {
            if self.effects[index].kind != effect.kind {
                self.effects[kept] = self.effects[index];
                kept += 1;
            }
        }
        self.effects[kept] = effect;
        self.effect_count = kept as u8 + 1;
    }
}

/// Ce que le moteur lit du round précédent : les deux cartes jouées et le vainqueur (Revenge / Confidence / After).
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct LastRound {
    pub ally_card: u8,
    pub enemy_card: u8,
    pub ally_won: bool,
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct State {
    pub nb_turn: u8,
    pub ally_first: bool, // l'allié joue en premier ce round
    pub ally: PlayerState,
    pub enemy: PlayerState,
    pub last_round: Option<LastRound>, // None au round 1
}

/// Un coup : la carte de la main, `pillz_fight` (1 + la mise, la pillz gratuite comprise) et la fury.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Action {
    pub card: u8,
    pub pillz: i16,
    pub fury: bool,
}

/// Valeurs de combat d'une carte à la fin du round : ce que le corpus exige de retrouver.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct SideOutcome {
    pub power: i16,
    pub damage: i16,
    pub attack: i16,
    pub win: bool,
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Outcome {
    pub ally: SideOutcome,
    pub enemy: SideOutcome,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn effect(kind: u8, value: i16) -> Effect {
        Effect { kind, value, borne: -1 }
    }

    #[test]
    fn un_effet_remplace_celui_de_meme_sorte_et_passe_en_dernier() {
        let mut player = PlayerState::new(12, 12, 0);
        player.register(effect(0, 2));
        player.register(effect(1, 3));
        player.register(effect(0, 5));

        assert_eq!(player.effects(), &[effect(1, 3), effect(0, 5)]);
    }

    /// La mémoïsation de l'IA hache l'état entier, cases d'effets libres comprises : deux joueurs arrivés au même
    /// jeu d'effets par des chemins différents doivent se hacher pareil, sans quoi la table double les entrées.
    #[test]
    fn deux_chemins_vers_les_memes_effets_donnent_le_meme_etat() {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut direct = PlayerState::new(12, 12, 0);
        direct.register(effect(3, 1));
        direct.register(effect(7, 4));

        let mut apres_remplacement = PlayerState::new(12, 12, 0);
        apres_remplacement.register(effect(7, 9));
        apres_remplacement.register(effect(3, 1));
        apres_remplacement.register(effect(7, 4));

        assert_eq!(direct, apres_remplacement);

        let empreinte = |state: &PlayerState| {
            let mut hasher = DefaultHasher::new();
            state.hash(&mut hasher);
            hasher.finish()
        };
        assert_eq!(empreinte(&direct), empreinte(&apres_remplacement));
    }

    #[test]
    fn les_cartes_jouees_tiennent_dans_le_masque() {
        let mut player = PlayerState::new(12, 12, 0);
        player.set_played(2);
        assert!(player.has_played(2));
        assert!(!player.has_played(0));
    }
}
