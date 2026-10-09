//! Le lecteur du corpus perd-il quelque chose ?
//!
//! Chaque famille est relue dans les types de `contract.rs`, puis réécrite **depuis ces types** en JSON canonique,
//! comme Python l'empreinte (`corpus.canonical` : clés triées, sans espace) : les entrées d'abord, puis les decks,
//! une ligne chacun. Le sha256 de cette réécriture ne peut égaler celui de `data/engine_digests.json` que si chaque
//! champ a survécu à la lecture : un entier tronqué, un effet perdu, un booléen inversé changent l'empreinte.

mod corpus;

use corpus::{CorpusDeck, Entry};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use ur_engine::contract::{Action, CompiledCapacity, CompiledCard, PlayerState, SideOutcome, State, HAND_SIZE};

fn digests() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/engine_digests.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/engine_digests.json introuvable");
    serde_json::from_str(&contents).expect("data/engine_digests.json illisible")
}

#[test]
fn chaque_famille_se_relit_a_l_identique() {
    let attendus = digests();
    let familles = attendus["families"]
        .as_object()
        .expect("pas de familles dans data/engine_digests.json");
    assert!(!familles.is_empty(), "pas de familles dans data/engine_digests.json");

    let mut ecarts = Vec::new();
    for (nom, attendu) in familles {
        let famille = corpus::read_family(nom);
        let mut empreinte = Sha256::new();
        for entry in &famille.entries {
            empreinte.update(serde_json::to_string(&entry_json(entry)).unwrap() + "\n");
        }
        for deck in &famille.decks {
            empreinte.update(serde_json::to_string(&deck_json(deck)).unwrap() + "\n");
        }
        let lu = json!({
            "entries": famille.entries.len(),
            "decks": famille.decks.len(),
            "sha256": format!("{:x}", empreinte.finalize()),
        });
        if &lu != attendu {
            ecarts.push(format!("{nom} : relu {lu}, attendu {attendu}"));
        }
    }
    assert!(
        ecarts.is_empty(),
        "familles qui ne se relisent pas à l'identique :\n{}",
        ecarts.join("\n")
    );
}

// --- Réécriture, au format de `dataclasses.asdict` (les tuples y deviennent des listes) --------
// Les objets de `serde_json` gardent leurs clés triées : c'est le `sort_keys` de Python.

fn entry_json(entry: &Entry) -> Value {
    json!({
        "id": entry.id,
        "deck": entry.deck,
        "state": state_json(&entry.state),
        "ally_action": action_json(&entry.ally_action),
        "enemy_action": action_json(&entry.enemy_action),
        "next_state": state_json(&entry.next_state),
        "outcome": {"ally": side_outcome_json(&entry.outcome.ally), "enemy": side_outcome_json(&entry.outcome.enemy)},
    })
}

fn state_json(state: &State) -> Value {
    json!({
        "nb_turn": state.nb_turn,
        "ally_first": state.ally_first,
        "ally": player_json(&state.ally),
        "enemy": player_json(&state.enemy),
        "last_round": state.last_round.map(|last| json!([last.ally_card, last.enemy_card, last.ally_won])),
    })
}

fn player_json(player: &PlayerState) -> Value {
    json!({
        "life": player.life,
        "pillz": player.pillz,
        "played": (0..HAND_SIZE).map(|card| player.has_played(card)).collect::<Vec<_>>(),
        "effects": player.effects().iter().map(|effect| json!([effect.kind, effect.value, effect.borne])).collect::<Vec<_>>(),
    })
}

fn action_json(action: &Action) -> Value {
    json!([action.card, action.pillz, action.fury])
}

fn side_outcome_json(side: &SideOutcome) -> Value {
    json!([side.power, side.damage, side.attack, side.win])
}

fn deck_json(corpus_deck: &CorpusDeck) -> Value {
    let deck = &corpus_deck.deck;
    json!({
        "ally": hand_json(&deck.ally, &corpus_deck.ally_names),
        "enemy": hand_json(&deck.enemy, &corpus_deck.enemy_names),
        "ally_start": deck.ally_start,
        "enemy_start": deck.enemy_start,
    })
}

fn hand_json(cards: &[CompiledCard], names: &[String]) -> Value {
    cards
        .iter()
        .zip(names)
        .map(|(card, name)| {
            json!({
                "name": name,
                "stars": card.stars,
                "clan": card.clan,
                "power": card.power,
                "damage": card.damage,
                "ability": card.ability.map(capacity_json),
                "bonus": card.bonus.map(capacity_json),
            })
        })
        .collect()
}

fn capacity_json(capacity: CompiledCapacity) -> Value {
    json!({
        "how": capacity.how,
        "target": capacity.target,
        "types": capacity.types,
        "value": capacity.value,
        "borne": capacity.borne,
        "conditions": capacity.conditions,
        "bet_over": capacity.bet_over,
        "bet_under": capacity.bet_under,
        "clans": capacity.clans,
    })
}
