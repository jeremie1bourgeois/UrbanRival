//! Les coups légaux et la fin de partie, transcrits de `UrbanPy/Backend_fastAPI/src/core/engine/reference.py`
//! (`legal_actions`, `terminal`) : avec `round::play`, les fonctions pures que la recherche appelle.

use crate::contract::{Action, PlayerState, State, FURY_COST, HAND_SIZE, NB_ROUNDS};

/// Les coups d'un camp, dans l'ordre de Python : chaque carte non jouée, chaque mise de 1 (la pillz gratuite seule) à
/// pillz + 1, sans fury puis avec fury si la mise et la fury tiennent dans les pillz. Le camp se désigne par son état
/// (`&state.ally` ou `&state.enemy`), seul ce que les coups lisent. Un itérateur : rien n'est alloué.
pub fn legal_actions(player: &PlayerState) -> impl Iterator<Item = Action> + '_ {
    (0..HAND_SIZE)
        .filter(|&card| !player.has_played(card))
        .flat_map(|card| card_actions(player, card))
}

/// Les coups d'une carte, dans l'ordre de `legal_actions` : les lignes ou les colonnes d'un bloc de mises. Que la
/// carte soit encore en main n'est pas vérifié.
pub fn card_actions(player: &PlayerState, card: usize) -> impl Iterator<Item = Action> {
    let pillz = player.pillz;
    (0..=pillz).flat_map(move |bet| {
        let action = Action { card: card as u8, pillz: bet + 1, fury: false };
        let fury = (bet + FURY_COST <= pillz).then_some(Action { fury: true, ..action });
        std::iter::once(action).chain(fury)
    })
}

/// La valeur de la partie pour l'allié si elle est finie (1 gagnée, 0,5 nulle, 0 perdue), None sinon : après le
/// dernier round, la plus grande vie gagne ; avant, un camp à 0 vie a perdu, et deux camps à 0 vie font match nul.
pub fn terminal(state: &State) -> Option<f64> {
    if state.nb_turn > NB_ROUNDS {
        return Some(match state.ally.life.cmp(&state.enemy.life) {
            std::cmp::Ordering::Greater => 1.0,
            std::cmp::Ordering::Less => 0.0,
            std::cmp::Ordering::Equal => 0.5,
        });
    }
    if state.ally.life == 0 && state.enemy.life == 0 {
        return Some(0.5);
    }
    if state.ally.life == 0 {
        return Some(0.0);
    }
    if state.enemy.life == 0 {
        return Some(1.0);
    }
    None
}
