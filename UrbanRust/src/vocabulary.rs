//! Vocabulaire figé du contrat, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py`.
//!
//! Les indices sont la monnaie d'échange entre les deux moteurs : un corpus écrit par le moteur Python se relit ici
//! sans traduction. Ils sont donc **figés** — ajouter une valeur, c'est l'ajouter en fin de tableau, jamais au milieu.
//! `tests/vocabulaire.rs` recalcule l'empreinte sha256 du vocabulaire et la compare à celle que Python a écrite dans
//! `data/engine_digests.json` : toute divergence de transcription, même une coquille, y apparaît.

pub const HOWS: [&str; 24] = [
    "", "Protection", "brawl", "cancel", "copy", "counter_attack", "degrowth", "equalizer", "exchange", "growth",
    "impose", "limitless", "nb_dam_opp", "nb_damage", "nb_life_left", "nb_life_lost", "nb_pillz_left", "nb_pillz_lost",
    "nb_pow_opp", "stop", "support", "tie_break", "tune_out", "immediate",
];

pub const TYPES: [&str; 23] = [
    "ability", "attack", "bonus", "combust", "consume", "counter_attack", "damage", "dope", "heal", "infiltrated",
    "ko", "life", "limitless", "pillz", "poison", "power", "reanimate", "recover", "regen", "repair", "tie_break",
    "toxine", "tune_out",
];

pub const CONDITIONS: [&str; 19] = [
    "after", "asymmetry", "backlash", "bet", "confidence", "courage", "defeat", "disunion", "infiltrated", "killshot",
    "perfect", "reprisal", "revenge", "stop", "symmetry", "team", "unison", "versus", "victory_defeat",
];

pub const TARGETS: [&str; 3] = ["ally", "enemy", "both"];

pub const CLANS: [&str; 36] = [
    "All Stars", "Bangers", "Berzerk", "Cosmohnuts", "Dominion", "Fang Pi Clang", "Freaks", "Frozn", "GHEIST",
    "GhosTown", "Hive", "Huracan", "Jungo", "Junkz", "Komboka", "La Junta", "Leader", "Montana", "Nightmare",
    "Oblivion", "Oculus", "Paradox", "Piranas", "Pussycats", "Raptors", "Rescue", "Riots", "Roots", "Sakrohm",
    "Sentinel", "Skeelz", "Tolvack", "Ulu Watu", "Uppers", "Vortex", "Zenith",
];

pub const EFFECT_KINDS: [&str; 8] = [
    "poison", "toxine", "heal", "regen", "dope", "repair", "consume", "combust",
];

/// Les indices lus par le moteur, nommés. Chacun est cherché dans son tableau à la compilation : un nom mal
/// orthographié fait échouer la compilation au lieu de désigner une autre valeur.
pub mod hows {
    use super::{position, HOWS};
    pub const NONE: u8 = position(&HOWS, "");
    pub const PROTECTION: u8 = position(&HOWS, "Protection");
    pub const BRAWL: u8 = position(&HOWS, "brawl");
    pub const CANCEL: u8 = position(&HOWS, "cancel");
    pub const COPY: u8 = position(&HOWS, "copy");
    pub const COUNTER_ATTACK: u8 = position(&HOWS, "counter_attack");
    pub const DEGROWTH: u8 = position(&HOWS, "degrowth");
    pub const EQUALIZER: u8 = position(&HOWS, "equalizer");
    pub const EXCHANGE: u8 = position(&HOWS, "exchange");
    pub const GROWTH: u8 = position(&HOWS, "growth");
    pub const IMPOSE: u8 = position(&HOWS, "impose");
    pub const LIMITLESS: u8 = position(&HOWS, "limitless");
    pub const NB_DAM_OPP: u8 = position(&HOWS, "nb_dam_opp");
    pub const NB_DAMAGE: u8 = position(&HOWS, "nb_damage");
    pub const NB_LIFE_LEFT: u8 = position(&HOWS, "nb_life_left");
    pub const NB_LIFE_LOST: u8 = position(&HOWS, "nb_life_lost");
    pub const NB_PILLZ_LEFT: u8 = position(&HOWS, "nb_pillz_left");
    pub const NB_PILLZ_LOST: u8 = position(&HOWS, "nb_pillz_lost");
    pub const NB_POW_OPP: u8 = position(&HOWS, "nb_pow_opp");
    pub const STOP: u8 = position(&HOWS, "stop");
    pub const SUPPORT: u8 = position(&HOWS, "support");
    pub const TIE_BREAK: u8 = position(&HOWS, "tie_break");
    pub const TUNE_OUT: u8 = position(&HOWS, "tune_out");
    pub const IMMEDIATE: u8 = position(&HOWS, "immediate");
}

pub mod types {
    use super::{position, TYPES};
    pub const ABILITY: u8 = position(&TYPES, "ability");
    pub const ATTACK: u8 = position(&TYPES, "attack");
    pub const BONUS: u8 = position(&TYPES, "bonus");
    pub const COMBUST: u8 = position(&TYPES, "combust");
    pub const CONSUME: u8 = position(&TYPES, "consume");
    pub const DAMAGE: u8 = position(&TYPES, "damage");
    pub const DOPE: u8 = position(&TYPES, "dope");
    pub const HEAL: u8 = position(&TYPES, "heal");
    pub const INFILTRATED: u8 = position(&TYPES, "infiltrated");
    pub const KO: u8 = position(&TYPES, "ko");
    pub const LIFE: u8 = position(&TYPES, "life");
    pub const PILLZ: u8 = position(&TYPES, "pillz");
    pub const POISON: u8 = position(&TYPES, "poison");
    pub const POWER: u8 = position(&TYPES, "power");
    pub const REANIMATE: u8 = position(&TYPES, "reanimate");
    pub const RECOVER: u8 = position(&TYPES, "recover");
    pub const REGEN: u8 = position(&TYPES, "regen");
    pub const REPAIR: u8 = position(&TYPES, "repair");
    pub const TOXINE: u8 = position(&TYPES, "toxine");
}

pub mod conditions {
    use super::{position, CONDITIONS};
    pub const AFTER: u8 = position(&CONDITIONS, "after");
    pub const ASYMMETRY: u8 = position(&CONDITIONS, "asymmetry");
    pub const BACKLASH: u8 = position(&CONDITIONS, "backlash");
    pub const BET: u8 = position(&CONDITIONS, "bet");
    pub const CONFIDENCE: u8 = position(&CONDITIONS, "confidence");
    pub const COURAGE: u8 = position(&CONDITIONS, "courage");
    pub const DEFEAT: u8 = position(&CONDITIONS, "defeat");
    pub const DISUNION: u8 = position(&CONDITIONS, "disunion");
    pub const INFILTRATED: u8 = position(&CONDITIONS, "infiltrated");
    pub const KILLSHOT: u8 = position(&CONDITIONS, "killshot");
    pub const PERFECT: u8 = position(&CONDITIONS, "perfect");
    pub const REPRISAL: u8 = position(&CONDITIONS, "reprisal");
    pub const REVENGE: u8 = position(&CONDITIONS, "revenge");
    pub const STOP: u8 = position(&CONDITIONS, "stop");
    pub const SYMMETRY: u8 = position(&CONDITIONS, "symmetry");
    pub const TEAM: u8 = position(&CONDITIONS, "team");
    pub const UNISON: u8 = position(&CONDITIONS, "unison");
    pub const VERSUS: u8 = position(&CONDITIONS, "versus");
    pub const VICTORY_DEFEAT: u8 = position(&CONDITIONS, "victory_defeat");
}

pub mod targets {
    use super::{position, TARGETS};
    pub const ALLY: u8 = position(&TARGETS, "ally");
    pub const ENEMY: u8 = position(&TARGETS, "enemy");
    pub const BOTH: u8 = position(&TARGETS, "both");
}

pub mod clans {
    use super::{position, CLANS};
    pub const LEADER: u8 = position(&CLANS, "Leader");
    pub const OCULUS: u8 = position(&CLANS, "Oculus");
}

pub mod effect_kinds {
    use super::{position, EFFECT_KINDS};
    pub const POISON: u8 = position(&EFFECT_KINDS, "poison");
    pub const TOXINE: u8 = position(&EFFECT_KINDS, "toxine");
    pub const HEAL: u8 = position(&EFFECT_KINDS, "heal");
    pub const REGEN: u8 = position(&EFFECT_KINDS, "regen");
    pub const DOPE: u8 = position(&EFFECT_KINDS, "dope");
    pub const REPAIR: u8 = position(&EFFECT_KINDS, "repair");
    pub const CONSUME: u8 = position(&EFFECT_KINDS, "consume");
    pub const COMBUST: u8 = position(&EFFECT_KINDS, "combust");
}

const fn position(vocabulary: &[&str], name: &str) -> u8 {
    let mut index = 0;
    while index < vocabulary.len() {
        if same_bytes(vocabulary[index].as_bytes(), name.as_bytes()) {
            return index as u8;
        }
        index += 1;
    }
    panic!("nom absent du vocabulaire");
}

const fn same_bytes(left: &[u8], right: &[u8]) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut index = 0;
    while index < left.len() {
        if left[index] != right[index] {
            return false;
        }
        index += 1;
    }
    true
}

/// Le JSON canonique de `corpus.VOCABULARY` : clés triées, sans espace, tel que Python l'empreinte.
pub fn canonical_json() -> String {
    let mut out = String::with_capacity(1024);
    out.push('{');
    for (index, (key, values)) in [
        ("clans", &CLANS[..]),
        ("conditions", &CONDITIONS[..]),
        ("effect_kinds", &EFFECT_KINDS[..]),
        ("hows", &HOWS[..]),
        ("targets", &TARGETS[..]),
        ("types", &TYPES[..]),
    ]
    .iter()
    .enumerate()
    {
        if index > 0 {
            out.push(',');
        }
        out.push('"');
        out.push_str(key);
        out.push_str("\":[");
        for (position, value) in values.iter().enumerate() {
            if position > 0 {
                out.push(',');
            }
            out.push('"');
            out.push_str(value);
            out.push('"');
        }
        out.push(']');
    }
    out.push('}');
    out
}

/// Indice d'un nom dans un tableau du vocabulaire, pour lire un corpus ou un deck écrit en clair.
pub fn index_of(vocabulary: &[&str], name: &str) -> Option<u8> {
    vocabulary
        .iter()
        .position(|entry| *entry == name)
        .map(|index| index as u8)
}
