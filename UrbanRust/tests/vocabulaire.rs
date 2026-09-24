//! Le vocabulaire transcrit ici est-il exactement celui du moteur Python ?
//!
//! Python empreinte son vocabulaire (`corpus.vocabulary_digest`) et écrit le sha256 dans `data/engine_digests.json`.
//! On recalcule la même empreinte depuis le tableau Rust : elle ne peut coïncider que si les six listes ont les mêmes
//! valeurs **dans le même ordre** — et l'ordre est ce qui donne leur sens aux indices d'un corpus.

use sha2::{Digest, Sha256};
use ur_engine::vocabulary;

fn digests() -> serde_json::Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../UrbanPy/Backend_fastAPI/data/engine_digests.json"
    );
    let contents = std::fs::read_to_string(path).expect("data/engine_digests.json introuvable");
    serde_json::from_str(&contents).expect("data/engine_digests.json illisible")
}

#[test]
fn le_vocabulaire_a_la_meme_empreinte_que_celui_de_python() {
    let attendu = digests()["vocabulary"]
        .as_str()
        .expect("pas d'empreinte de vocabulaire")
        .to_string();

    let empreinte = format!("{:x}", Sha256::digest(vocabulary::canonical_json().as_bytes()));

    assert_eq!(
        empreinte, attendu,
        "vocabulaire divergent — un nom, un ordre ou une liste ne colle pas"
    );
}

#[test]
fn un_nom_se_retrouve_a_son_indice() {
    assert_eq!(vocabulary::index_of(&vocabulary::CLANS, "Nightmare"), Some(18));
    assert_eq!(vocabulary::index_of(&vocabulary::TARGETS, "both"), Some(2));
    assert_eq!(vocabulary::index_of(&vocabulary::HOWS, "inconnu"), None);
}
