//! Un round, transcrit de `UrbanPy/Backend_fastAPI/src/core/use_cases/process_round.py` et des niveaux de capacités
//! qu'il appelle (un fichier par niveau, comme côté Python).
//!
//! C'est la version simple, la référence lisible du moteur Rust : chaque fonction porte le nom de celle qu'elle
//! transcrit, pour qu'on relise les deux côte à côte. Les versions rapides (bloc de mises, étape 1.4) se vérifient
//! contre elle. Le portage se fait par pas ; ce qui est porté se lit dans `UrbanRust/README.md`.

mod level4;

use crate::contract::{Action, CompiledCard, Deck, LastRound, Outcome, PlayerState, SideOutcome, State};

const ALLY: usize = 0;
const ENEMY: usize = 1;
const SIDES: [usize; 2] = [ALLY, ENEMY];

const FURY_COST: i16 = 3;
const FURY_DAMAGE: i16 = 2;

/// Une carte jouée, le temps du round : ce que `init_fight_data` prépare et que les niveaux modifient.
#[derive(Clone, Copy)]
struct Fighter {
    index: usize, // dans la main
    power: i16,   // power_fight
    damage: i16,  // damage_fight
    attack: i16,
    pillz: i16, // pillz_fight : la mise, pillz gratuite comprise
    fury: bool,
    win: bool,
    cancelled: u32, // masque sur TYPES (life, pillz) : modifications annulées par un Cancel adverse (cancelled_modifs)
}

/// La partie le temps d'un round : `Game` côté Python, réduite à ce que le round lit et écrit.
struct Round<'a> {
    deck: &'a Deck,
    nb_turn: u8,
    ally_first: bool, // game.turn
    players: [PlayerState; 2],
    fighters: [Fighter; 2],
}

/// Joue un round : l'état suivant et l'issue du combat, comme `reference.play`.
pub fn play(deck: &Deck, state: &State, ally_action: Action, enemy_action: Action) -> (State, Outcome) {
    let mut round = Round::new(deck, state, [ally_action, enemy_action]);
    round.process_round();
    round.finish()
}

impl Round<'_> {
    /// Les mises sont prélevées et les cartes préparées (`init_fight_data`).
    fn new<'a>(deck: &'a Deck, state: &State, actions: [Action; 2]) -> Round<'a> {
        let mut players = [state.ally, state.enemy];
        for side in SIDES {
            players[side].pillz -= (actions[side].pillz - 1) + FURY_COST * actions[side].fury as i16;
        }
        let fighters = SIDES.map(|side| {
            let action = actions[side];
            let card = hand(deck, side)[action.card as usize];
            Fighter {
                index: action.card as usize,
                power: card.power,
                damage: card.damage,
                attack: 0,
                pillz: action.pillz,
                fury: action.fury,
                win: false,
                cancelled: 0,
            }
        });
        Round {
            deck,
            nb_turn: state.nb_turn,
            ally_first: state.ally_first,
            players,
            fighters,
        }
    }

    fn card(&self, side: usize) -> &CompiledCard {
        &hand(self.deck, side)[self.fighters[side].index]
    }

    fn process_round(&mut self) {
        for fighter in &mut self.fighters {
            if fighter.fury {
                fighter.damage += FURY_DAMAGE;
            }
        }
        for fighter in &mut self.fighters {
            fighter.attack += fighter.power * fighter.pillz;
        }

        self.resolve_combat();

        if self.players.iter().all(|player| player.life > 0) {
            self.apply_capacity_lvl_4();
        }
    }

    fn resolve_combat(&mut self) {
        let (ally, enemy) = (&self.fighters[ALLY], &self.fighters[ENEMY]);
        let (ally_stars, enemy_stars) = (self.card(ALLY).stars, self.card(ENEMY).stars);
        let ally_wins = if ally.attack != enemy.attack {
            ally.attack > enemy.attack
        } else if ally_stars != enemy_stars {
            ally_stars < enemy_stars // moins d'étoiles gagne
        } else {
            self.ally_first
        };
        let (winner, loser) = if ally_wins { (ALLY, ENEMY) } else { (ENEMY, ALLY) };
        let damage = self.fighters[winner].damage;
        let loser_player = &mut self.players[loser];
        loser_player.life = (loser_player.life - damage).max(0);
        self.fighters[ALLY].win = ally_wins;
        self.fighters[ENEMY].win = !ally_wins;
    }

    /// L'état suivant (`state_from_game`) et l'issue du combat.
    fn finish(mut self) -> (State, Outcome) {
        for side in SIDES {
            self.players[side].set_played(self.fighters[side].index);
        }
        let (ally, enemy) = (self.fighters[ALLY], self.fighters[ENEMY]);
        let state = State {
            nb_turn: self.nb_turn + 1,
            ally_first: !self.ally_first,
            ally: self.players[ALLY],
            enemy: self.players[ENEMY],
            last_round: Some(LastRound {
                ally_card: ally.index as u8,
                enemy_card: enemy.index as u8,
                ally_won: ally.win,
            }),
        };
        (
            state,
            Outcome { ally: side_outcome(&ally), enemy: side_outcome(&enemy) },
        )
    }
}

fn hand(deck: &Deck, side: usize) -> &[CompiledCard] {
    if side == ALLY {
        &deck.ally
    } else {
        &deck.enemy
    }
}

fn side_outcome(fighter: &Fighter) -> SideOutcome {
    SideOutcome {
        power: fighter.power,
        damage: fighter.damage,
        attack: fighter.attack,
        win: fighter.win,
    }
}

const fn bit(index: u8) -> u32 {
    1 << index
}
