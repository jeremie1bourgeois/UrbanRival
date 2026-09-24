//! Vocabulaire figé du contrat, transcrit de `UrbanPy/Backend_fastAPI/src/core/engine/contract.py`.
//!
//! Les indices sont la monnaie d'échange entre les deux moteurs : un corpus écrit par le moteur Python se relit ici
//! sans traduction. Ils sont donc **figés** — ajouter une valeur, c'est l'ajouter en fin de tableau, jamais au milieu.
//! `tests/vocabulaire.rs` recalcule l'empreinte sha256 du vocabulaire et la compare à celle que Python a écrite dans
//! `data/engine_digests.json` : toute divergence de transcription, même une coquille, y apparaît.

pub const HOWS: [&str; 23] = [
    "", "Protection", "brawl", "cancel", "copy", "counter_attack", "degrowth", "equalizer", "exchange", "growth",
    "impose", "limitless", "nb_dam_opp", "nb_damage", "nb_life_left", "nb_life_lost", "nb_pillz_left", "nb_pillz_lost",
    "nb_pow_opp", "stop", "support", "tie_break", "tune_out",
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
