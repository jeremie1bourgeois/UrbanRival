//! Le test différentiel : chaque round du corpus, rejoué par le moteur Rust, redonne-t-il exactement l'état suivant
//! et l'issue du combat que le moteur Python a enregistrés ?
//!
//! Toutes les familles sont identiques à 100 % : un écart, après un changement de règle côté Python (corpus
//! régénéré) ou d'une optimisation côté Rust, fait échouer le test avec les cas qui divergent.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::collections::BTreeMap;

use corpus::Entry;
use ur_engine::round::play;

/// Les familles de `scenarios.FAMILIES`, celles de `data/engine_digests.json`.
const FAMILIES: [&str; 10] = [
    "solo", "interactions", "planchers", "persistants", "leaders", "oculus", "combat", "aleatoire", "masse", "reels",
];

#[test]
fn chaque_round_du_corpus_est_identique() {
    let reports: Vec<String> = FAMILIES.iter().filter_map(|name| divergences(name)).collect();
    assert!(
        reports.is_empty(),
        "rounds qui divergent du moteur Python :\n{}",
        reports.join("\n")
    );
}

/// Le rapport des rounds de la famille qui divergent, None s'il n'y en a aucun.
fn divergences(name: &str) -> Option<String> {
    let family = corpus::read_family(name);
    let replay = |entry: &Entry| {
        let deck = &family.decks[entry.deck].deck;
        play(deck, &entry.state, entry.ally_action, entry.enemy_action)
    };
    let divergent: Vec<&Entry> = family
        .entries
        .iter()
        .filter(|entry| replay(entry) != (entry.next_state, entry.outcome))
        .collect();
    if divergent.is_empty() {
        return None;
    }
    let report = divergence_report(&divergent, |entry| format!("{:?}", replay(entry)));
    Some(format!(
        "{name} : {} rounds sur {} divergent\n{report}",
        divergent.len(),
        family.entries.len()
    ))
}

/// Les groupes qui divergent le plus (les trois premiers segments de l'identifiant ; pour `solo`, « famille/
/// emplacement/capacité »), chacun avec un exemple : ce que Python attend, ce que Rust donne.
fn divergence_report(divergent: &[&Entry], replay: impl Fn(&Entry) -> String) -> String {
    let mut groups: BTreeMap<String, Vec<&Entry>> = BTreeMap::new();
    for entry in divergent {
        let key = entry.id.splitn(4, '/').take(3).collect::<Vec<_>>().join("/");
        groups.entry(key).or_default().push(entry);
    }
    let mut groups: Vec<_> = groups.into_iter().collect();
    groups.sort_by_key(|(_, entries)| std::cmp::Reverse(entries.len()));
    let mut report = String::new();
    for (key, entries) in groups.iter().take(15) {
        let example = entries[0];
        report += &format!(
            "  {} × {key}\n    {}\n    attendu ({:?}, {:?})\n    obtenu  {}\n",
            entries.len(),
            example.id,
            example.next_state,
            example.outcome,
            replay(example)
        );
    }
    if groups.len() > 15 {
        report += &format!("  … et {} autres groupes\n", groups.len() - 15);
    }
    report
}
