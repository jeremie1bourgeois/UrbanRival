//! Lecture du corpus de non-régression écrit par le moteur Python (`src/core/engine/corpus.py`) : chaque famille se
//! relit dans les types de `contract.rs`.
//!
//! Ce module vit dans les tests, pas dans la crate : le moteur reste sans dépendance, seuls les tests lisent du JSON.
//! Format, par famille : `<famille>.decks.json` (la liste des decks) et `<famille>.jsonl` (une entrée par ligne, son
//! deck désigné par l'indice dans cette liste). Générés sous Windows, les fichiers finissent leurs lignes par `\r\n` :
//! la lecture accepte les deux fins de ligne. `regles.jsonl`, à part, donne les coups légaux et la fin de partie.

use serde_json::Value;
use ur_engine::contract::{
    Action, CompiledCapacity, CompiledCard, Deck, Effect, LastRound, Outcome, PlayerState, SideOutcome, State,
    HAND_SIZE,
};

pub const CORPUS_DIR: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../UrbanPy/Backend_fastAPI/data/engine_corpus"
);

/// Un deck du corpus et le nom de ses cartes : le moteur ne lit pas les noms, le corpus les garde.
pub struct CorpusDeck {
    pub deck: Deck,
    pub ally_names: [String; HAND_SIZE],
    pub enemy_names: [String; HAND_SIZE],
}

/// Un round joué par le moteur Python : l'état et les deux coups, puis ce qu'il en a tiré.
pub struct Entry {
    pub id: String,
    pub deck: usize, // indice dans `Family::decks`
    pub state: State,
    pub ally_action: Action,
    pub enemy_action: Action,
    pub next_state: State,
    pub outcome: Outcome,
}

pub struct Family {
    pub decks: Vec<CorpusDeck>,
    pub entries: Vec<Entry>,
}

/// Un état et ce que le moteur Python en dit : les coups légaux de chaque camp, dans son ordre, et la fin de partie.
pub struct RulesEntry {
    pub state: State,
    pub ally_actions: Vec<Action>,
    pub enemy_actions: Vec<Action>,
    pub terminal: Option<f64>,
}

/// Une partie du banc d'essai (`data/engine_bench.json`) : son deck et l'état de début de chaque round, du premier au
/// quatrième (`states[0]` : le round 1).
pub struct BenchGame {
    pub id: String,
    pub deck: Deck,
    pub states: Vec<State>,
}

type Parsed<T> = Result<T, String>;

/// Lit les deux fichiers de la famille ; s'arrête au premier deck ou à la première ligne illisible, en le nommant.
pub fn read_family(name: &str) -> Family {
    let decks_path = format!("{CORPUS_DIR}/{name}.decks.json");
    let decks_json: Value =
        serde_json::from_str(&read_file(&decks_path)).unwrap_or_else(|error| panic!("{decks_path} : {error}"));
    let decks = decks_json
        .as_array()
        .unwrap_or_else(|| panic!("{decks_path} : liste de decks attendue"))
        .iter()
        .enumerate()
        .map(|(index, fields)| deck(fields).unwrap_or_else(|error| panic!("{decks_path}, deck {index} : {error}")))
        .collect();

    let entries_path = format!("{CORPUS_DIR}/{name}.jsonl");
    let entries = read_file(&entries_path)
        .lines()
        .enumerate()
        .map(|(index, line)| {
            entry(line).unwrap_or_else(|error| panic!("{entries_path}, ligne {} : {error}", index + 1))
        })
        .collect();

    Family { decks, entries }
}

pub fn read_rules() -> Vec<RulesEntry> {
    let path = format!("{CORPUS_DIR}/regles.jsonl");
    read_file(&path)
        .lines()
        .enumerate()
        .map(|(index, line)| rules_entry(line).unwrap_or_else(|error| panic!("{path}, ligne {} : {error}", index + 1)))
        .collect()
}

/// Le banc d'essai, versionné, écrit par `scripts/build_engine_bench.py`.
pub fn read_bench() -> Vec<BenchGame> {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/engine_bench.json"
    );
    let bench: Value = serde_json::from_str(&read_file(path)).unwrap_or_else(|error| panic!("{path} : {error}"));
    bench
        .as_array()
        .unwrap_or_else(|| panic!("{path} : liste de parties attendue"))
        .iter()
        .map(|game| BenchGame {
            id: game["id"].as_str().expect("identifiant").to_string(),
            deck: parse_deck(&game["deck"]).deck,
            states: game["states"]
                .as_array()
                .expect("états")
                .iter()
                .map(parse_state)
                .collect(),
        })
        .collect()
}

/// Un deck écrit comme dans `<famille>.decks.json` (`dataclasses.asdict`), lu hors du corpus.
pub fn parse_deck(fields: &Value) -> CorpusDeck {
    deck(fields).unwrap_or_else(|error| panic!("deck illisible : {error}"))
}

/// Un état écrit comme dans le corpus (`dataclasses.asdict`), lu hors du corpus.
pub fn parse_state(fields: &Value) -> State {
    state(fields).unwrap_or_else(|error| panic!("état illisible : {error}"))
}

fn read_file(path: &str) -> String {
    std::fs::read_to_string(path).unwrap_or_else(|error| {
        panic!("{path} : {error} — le corpus se génère avec scripts/build_engine_corpus.py (depuis UrbanPy/Backend_fastAPI)")
    })
}

// --- Valeurs élémentaires ---------------------------------------------------------------------

fn int<T: TryFrom<i64>>(value: &Value) -> Parsed<T> {
    value
        .as_i64()
        .and_then(|number| T::try_from(number).ok())
        .ok_or_else(|| {
            format!(
                "{value} : entier attendu, dans les bornes de {}",
                std::any::type_name::<T>()
            )
        })
}

fn boolean(value: &Value) -> Parsed<bool> {
    value.as_bool().ok_or_else(|| format!("{value} : booléen attendu"))
}

fn text(value: &Value) -> Parsed<String> {
    value
        .as_str()
        .map(str::to_string)
        .ok_or_else(|| format!("{value} : texte attendu"))
}

/// Une liste de longueur fixe : c'est ainsi que Python écrit ses tuples.
fn tuple<const N: usize>(value: &Value) -> Parsed<&[Value; N]> {
    value
        .as_array()
        .and_then(|items| <&[Value; N]>::try_from(items.as_slice()).ok())
        .ok_or_else(|| format!("{value} : liste de {N} éléments attendue"))
}

// --- Deck -------------------------------------------------------------------------------------

fn deck(fields: &Value) -> Parsed<CorpusDeck> {
    let (ally, ally_names) = hand(&fields["ally"])?;
    let (enemy, enemy_names) = hand(&fields["enemy"])?;
    let deck = Deck {
        ally,
        enemy,
        ally_start: start(&fields["ally_start"])?,
        enemy_start: start(&fields["enemy_start"])?,
    };
    Ok(CorpusDeck { deck, ally_names, enemy_names })
}

fn hand(value: &Value) -> Parsed<([CompiledCard; HAND_SIZE], [String; HAND_SIZE])> {
    let cards = tuple::<HAND_SIZE>(value)?
        .iter()
        .map(card)
        .collect::<Parsed<Vec<_>>>()?;
    let names: [String; HAND_SIZE] = std::array::from_fn(|index| cards[index].1.clone());
    let compiled = std::array::from_fn(|index| CompiledCard {
        character: names.iter().position(|name| *name == names[index]).unwrap() as u8,
        ..cards[index].0
    });
    Ok((compiled, names))
}

/// La carte, avec `character` à 0 : il dépend de toute la main, `hand` le pose.
fn card(fields: &Value) -> Parsed<(CompiledCard, String)> {
    let card = CompiledCard {
        character: 0,
        stars: int(&fields["stars"])?,
        clan: int(&fields["clan"])?,
        power: int(&fields["power"])?,
        damage: int(&fields["damage"])?,
        ability: capacity(&fields["ability"])?,
        bonus: capacity(&fields["bonus"])?,
    };
    Ok((card, text(&fields["name"])?))
}

fn capacity(fields: &Value) -> Parsed<Option<CompiledCapacity>> {
    if fields.is_null() {
        return Ok(None);
    }
    Ok(Some(CompiledCapacity {
        how: int(&fields["how"])?,
        target: int(&fields["target"])?,
        types: int(&fields["types"])?,
        value: int(&fields["value"])?,
        borne: int(&fields["borne"])?,
        conditions: int(&fields["conditions"])?,
        bet_over: int(&fields["bet_over"])?,
        bet_under: int(&fields["bet_under"])?,
        clans: int(&fields["clans"])?,
    }))
}

fn start(value: &Value) -> Parsed<(i16, i16)> {
    let [life, pillz] = tuple(value)?;
    Ok((int(life)?, int(pillz)?))
}

// --- Entrée -----------------------------------------------------------------------------------

fn entry(line: &str) -> Parsed<Entry> {
    let fields: Value = serde_json::from_str(line).map_err(|error| error.to_string())?;
    Ok(Entry {
        id: text(&fields["id"])?,
        deck: int(&fields["deck"])?,
        state: state(&fields["state"])?,
        ally_action: action(&fields["ally_action"])?,
        enemy_action: action(&fields["enemy_action"])?,
        next_state: state(&fields["next_state"])?,
        outcome: Outcome {
            ally: side_outcome(&fields["outcome"]["ally"])?,
            enemy: side_outcome(&fields["outcome"]["enemy"])?,
        },
    })
}

fn state(fields: &Value) -> Parsed<State> {
    Ok(State {
        nb_turn: int(&fields["nb_turn"])?,
        ally_first: boolean(&fields["ally_first"])?,
        ally: player_state(&fields["ally"])?,
        enemy: player_state(&fields["enemy"])?,
        last_round: last_round(&fields["last_round"])?,
    })
}

fn player_state(fields: &Value) -> Parsed<PlayerState> {
    let mut played = 0;
    for (index, card) in tuple::<HAND_SIZE>(&fields["played"])?.iter().enumerate() {
        if boolean(card)? {
            played |= 1 << index;
        }
    }
    let mut player = PlayerState::new(int(&fields["life"])?, int(&fields["pillz"])?, played);
    // `register` remplace l'effet de même sorte : un état qui en porterait deux serait relu amputé, et l'empreinte
    // de `tests/lecture_corpus.rs` le signalerait.
    for effect in fields["effects"].as_array().ok_or("liste d'effets attendue")? {
        let [kind, value, borne] = tuple(effect)?;
        player.register(Effect { kind: int(kind)?, value: int(value)?, borne: int(borne)? });
    }
    Ok(player)
}

fn last_round(value: &Value) -> Parsed<Option<LastRound>> {
    if value.is_null() {
        return Ok(None);
    }
    let [ally_card, enemy_card, ally_won] = tuple(value)?;
    Ok(Some(LastRound {
        ally_card: int(ally_card)?,
        enemy_card: int(enemy_card)?,
        ally_won: boolean(ally_won)?,
    }))
}

// --- Règles -----------------------------------------------------------------------------------

fn rules_entry(line: &str) -> Parsed<RulesEntry> {
    let fields: Value = serde_json::from_str(line).map_err(|error| error.to_string())?;
    let actions = |side: &str| -> Parsed<Vec<Action>> {
        let listed = &fields["legal_actions"][side];
        listed
            .as_array()
            .ok_or_else(|| format!("{listed} : liste de coups attendue"))?
            .iter()
            .map(action)
            .collect()
    };
    let terminal = &fields["terminal"];
    Ok(RulesEntry {
        state: state(&fields["state"])?,
        ally_actions: actions("ally")?,
        enemy_actions: actions("enemy")?,
        terminal: if terminal.is_null() {
            None
        } else {
            Some(
                terminal
                    .as_f64()
                    .ok_or_else(|| format!("{terminal} : nombre attendu"))?,
            )
        },
    })
}

fn action(value: &Value) -> Parsed<Action> {
    let [card, pillz, fury] = tuple(value)?;
    Ok(Action { card: int(card)?, pillz: int(pillz)?, fury: boolean(fury)? })
}

fn side_outcome(value: &Value) -> Parsed<SideOutcome> {
    let [power, damage, attack, win] = tuple(value)?;
    Ok(SideOutcome {
        power: int(power)?,
        damage: int(damage)?,
        attack: int(attack)?,
        win: boolean(win)?,
    })
}
