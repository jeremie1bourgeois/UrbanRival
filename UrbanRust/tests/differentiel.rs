//! Le test différentiel : chaque round du corpus, rejoué par le moteur Rust, redonne-t-il exactement l'état suivant
//! et l'issue du combat que le moteur Python a enregistrés ?
//!
//! Le portage avance par pas : chaque famille a un cliquet, le nombre de rounds déjà identiques, qui monte à chaque
//! pas jusqu'à la famille entière. Un pas qui fait baisser ce nombre fait échouer le test. `cargo test --test
//! differentiel -- --nocapture` affiche les capacités qui divergent encore.

#[allow(dead_code)] // chaque test ne lit qu'une partie de ce que le lecteur donne
mod corpus;

use std::collections::BTreeMap;

use corpus::Entry;
use ur_engine::round::play;

/// Rounds de la famille `solo` identiques au moteur Python (53 734 au total).
const SOLO_IDENTIQUES: usize = 45_640;

#[test]
fn solo() {
    compare_family("solo", SOLO_IDENTIQUES);
}

fn compare_family(name: &str, minimum: usize) {
    let family = corpus::read_family(name);
    let divergent: Vec<&Entry> = family
        .entries
        .iter()
        .filter(|entry| {
            let deck = &family.decks[entry.deck].deck;
            play(deck, &entry.state, entry.ally_action, entry.enemy_action) != (entry.next_state, entry.outcome)
        })
        .collect();
    let identical = family.entries.len() - divergent.len();
    let report = divergence_report(&divergent, |entry| {
        let deck = &family.decks[entry.deck].deck;
        format!("{:?}", play(deck, &entry.state, entry.ally_action, entry.enemy_action))
    });
    eprintln!(
        "{name} : {identical} rounds identiques sur {}\n{report}",
        family.entries.len()
    );
    assert!(
        identical >= minimum,
        "{name} : {identical} rounds identiques, le cliquet en exige {minimum}\n{report}"
    );
}

/// Les capacités qui divergent le plus (l'identifiant d'une entrée commence par « famille/emplacement/capacité »),
/// chacune avec un exemple : ce que Python attend, ce que Rust donne.
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
        report += &format!("  … et {} autres capacités\n", groups.len() - 15);
    }
    report
}
