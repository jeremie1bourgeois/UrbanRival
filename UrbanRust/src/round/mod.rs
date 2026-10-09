//! Un round, transcrit de `UrbanPy/Backend_fastAPI/src/core/use_cases/process_round.py` et des niveaux de capacités
//! qu'il appelle (un fichier par niveau, comme côté Python).
//!
//! C'est la version simple, la référence lisible du moteur Rust : chaque fonction porte le nom de celle qu'elle
//! transcrit, pour qu'on relise les deux côte à côte. Les versions rapides (bloc de mises, étape 1.4) se vérifient
//! contre elle. Le portage se fait par pas ; ce qui est porté se lit dans `UrbanRust/README.md`.

mod clan;
mod level1;
mod level2;
mod level4;
mod multipliers;

use crate::contract::{
    Action, CompiledCapacity, CompiledCard, Deck, LastRound, Outcome, PlayerState, SideOutcome, State,
};
use crate::vocabulary::{clans, conditions, hows, targets, types};

const ALLY: usize = 0;
const ENEMY: usize = 1;
const SIDES: [usize; 2] = [ALLY, ENEMY];

/// Emplacements de combat d'une carte jouée, dans l'ordre de `FIGHT_SLOTS` : son pouvoir, son bonus, et la
/// capacité « Team: » du Leader de l'équipe.
const ABILITY: usize = 0;
const BONUS: usize = 1;
const LEADER: usize = 2;
const SLOTS: [usize; 3] = [ABILITY, BONUS, LEADER];

const POWER: u32 = bit(types::POWER);
const DAMAGE: u32 = bit(types::DAMAGE);
const ATTACK: u32 = bit(types::ATTACK);
const LIFE: u32 = bit(types::LIFE);
const PILLZ: u32 = bit(types::PILLZ);

const FURY_COST: i16 = 3;
const FURY_DAMAGE: i16 = 2;

/// Conditions vérifiées en début de round (`unmet_condition`) ; les autres (stop, killshot, perfect, defeat,
/// backlash, victory_defeat) le sont plus tard.
const START_CONDITIONS: u32 = bit(conditions::REVENGE)
    | bit(conditions::CONFIDENCE)
    | bit(conditions::COURAGE)
    | bit(conditions::REPRISAL)
    | bit(conditions::SYMMETRY)
    | bit(conditions::ASYMMETRY)
    | bit(conditions::UNISON)
    | bit(conditions::DISUNION)
    | bit(conditions::VERSUS)
    | bit(conditions::AFTER)
    | bit(conditions::INFILTRATED)
    | bit(conditions::BET);

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
    slots: [Option<CompiledCapacity>; 3], // ability_fight, bonus_fight, leader_fight
    cancelled: u32, // masque sur TYPES (life, pillz) : modifications annulées par un Cancel adverse (cancelled_modifs)
}

impl Fighter {
    fn stat_mut(&mut self, stat: u32) -> &mut i16 {
        match stat {
            POWER => &mut self.power,
            DAMAGE => &mut self.damage,
            _ => &mut self.attack,
        }
    }

    fn has_how(&self, how: u8) -> bool {
        self.slots.iter().flatten().any(|capacity| capacity.how == how)
    }
}

/// La partie le temps d'un round : `Game` côté Python, réduite à ce que le round lit et écrit.
struct Round<'a> {
    deck: &'a Deck,
    nb_turn: u8,
    ally_first: bool, // game.turn
    last_round: Option<LastRound>,
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
                slots: [card.ability, card.bonus, None],
                cancelled: 0,
            }
        });
        Round {
            deck,
            nb_turn: state.nb_turn,
            ally_first: state.ally_first,
            last_round: state.last_round,
            players,
            fighters,
        }
    }

    fn hand(&self, side: usize) -> &[CompiledCard] {
        hand(self.deck, side)
    }

    fn card(&self, side: usize) -> &CompiledCard {
        &self.hand(side)[self.fighters[side].index]
    }

    fn process_round(&mut self) {
        for side in SIDES {
            self.apply_infiltrated_bonus(side);
        }
        for side in SIDES {
            if !clan::is_clan_bonus_active(self.hand(side), self.fighters[side].index) {
                self.fighters[side].slots[BONUS] = None;
            }
        }
        for side in SIDES {
            self.fighters[side].slots[LEADER] = self.leader_team_capacity(side);
        }
        self.apply_leader_modes();

        // Copy: Opp. Ability / Bonus copie le texte adverse, conditions comprises, puis les conditions de la copie sont
        // évaluées pour le copieur (combat réel 1349481) : instantané avant la première passe, seconde passe après
        let copy_sources = self.fighters.map(|fighter| fighter.slots);
        self.drop_unmet_conditions();
        self.apply_copies(&copy_sources);
        self.drop_unmet_conditions();

        self.apply_capacity_lvl_1();
        self.apply_capacity_lvl_2(POWER | DAMAGE);

        for fighter in &mut self.fighters {
            if fighter.fury {
                fighter.damage += FURY_DAMAGE;
            }
        }
        for fighter in &mut self.fighters {
            fighter.attack += fighter.power * fighter.pillz;
        }
        // une fois l'attaque de base connue : sinon un « -X Opp Attack, Min Y » s'appliquerait à une attaque nulle
        self.apply_capacity_lvl_2(ATTACK);

        // Tune Out : le round se résout aux pillz, les deux cartes à puissance 1, fury non comptée (combat 1248952)
        if self.consume_tune_out(ALLY) | self.consume_tune_out(ENEMY) {
            for fighter in &mut self.fighters {
                fighter.power = 1;
                fighter.attack = fighter.pillz;
            }
        }

        self.apply_killshot_condition(ALLY);
        self.apply_killshot_condition(ENEMY);
        self.apply_perfect_condition(ALLY);
        self.apply_perfect_condition(ENEMY);

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
        } else if ally.has_how(hows::TIE_BREAK) != enemy.has_how(hows::TIE_BREAK) {
            ally.has_how(hows::TIE_BREAK) // Tie-break (Solomon) : gagne toute égalité
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

    /// Retire un Tune Out (survivant à la phase des Stops) de la carte ; vrai s'il y en avait un.
    fn consume_tune_out(&mut self, side: usize) -> bool {
        let found = self.fighters[side].has_how(hows::TUNE_OUT);
        for slot in &mut self.fighters[side].slots {
            if slot.is_some_and(|capacity| capacity.how == hows::TUNE_OUT) {
                *slot = None;
            }
        }
        found
    }

    /// Killshot : attaque au moins double de l'attaque adverse ; la condition est consommée, ou la capacité retirée.
    fn apply_killshot_condition(&mut self, side: usize) {
        let (own, opp) = (self.fighters[side].attack, self.fighters[ENEMY - side].attack);
        self.apply_deferred_condition(side, conditions::KILLSHOT, own > 0 && own >= 2 * opp);
    }

    /// Perfect : l'écart d'attaque est strictement inférieur à la puissance de la carte (une pillz de moins n'aurait
    /// pas gagné) ; la victoire est exigée au niveau 3.
    fn apply_perfect_condition(&mut self, side: usize) {
        let fighter = &self.fighters[side];
        let met = fighter.attack - self.fighters[ENEMY - side].attack < fighter.power;
        self.apply_deferred_condition(side, conditions::PERFECT, met);
    }

    fn apply_deferred_condition(&mut self, side: usize, condition: u8, met: bool) {
        for slot in &mut self.fighters[side].slots {
            if let Some(capacity) = slot {
                if capacity.conditions & bit(condition) != 0 {
                    if met {
                        capacity.conditions &= !bit(condition);
                    } else {
                        *slot = None;
                    }
                }
            }
        }
    }

    /// Les conditions de début de round de chaque capacité : remplies, elles sont consommées ; sinon la capacité
    /// est retirée.
    fn drop_unmet_conditions(&mut self) {
        for side in SIDES {
            for slot in SLOTS {
                if let Some(mut capacity) = self.fighters[side].slots[slot] {
                    let met = self.start_conditions_met(&capacity, side);
                    capacity.conditions &= !START_CONDITIONS;
                    self.fighters[side].slots[slot] = met.then_some(capacity);
                }
            }
        }
    }

    /// `unmet_condition` : vrai si toutes les conditions de début de round de la capacité sont remplies.
    fn start_conditions_met(&self, capacity: &CompiledCapacity, side: usize) -> bool {
        let has = |condition: u8| capacity.conditions & bit(condition) != 0;
        let listed = |clan: u8| capacity.clans >> clan & 1 == 1;
        if has(conditions::TEAM) {
            return false; // ability de Leader : jamais jouée comme ability de carte (voir leader_team_capacity)
        }
        let opp = ENEMY - side;
        let (own_index, opp_index) = (self.fighters[side].index, self.fighters[opp].index);
        let hand = self.hand(side);
        let own_won_last = self.last_round.map(|last| last.ally_won == (side == ALLY));
        let plays_first = self.ally_first == (side == ALLY);
        let mono_clan = || hand.iter().all(|card| card.clan == hand[own_index].clan);
        let previous_card = self
            .last_round
            .map(|last| if side == ALLY { last.ally_card } else { last.enemy_card });

        !(has(conditions::REVENGE) && own_won_last != Some(false)
            || has(conditions::CONFIDENCE) && own_won_last != Some(true)
            || has(conditions::COURAGE) && !plays_first
            || has(conditions::REPRISAL) && plays_first
            || has(conditions::SYMMETRY) && own_index != opp_index
            || has(conditions::ASYMMETRY) && own_index == opp_index
            || has(conditions::UNISON) && !mono_clan()
            || has(conditions::DISUNION) && mono_clan()
            // « Versus » : au moins une carte du clan dans la main adverse, pas seulement la carte en face
            || has(conditions::VERSUS) && !self.hand(opp).iter().any(|card| listed(card.clan))
            // « After » : ma carte du round précédent est du clan (jamais au round 1)
            || has(conditions::AFTER) && !previous_card.is_some_and(|index| listed(hand[index as usize].clan))
            || has(conditions::INFILTRATED) && !clan::clan_for_bonus(hand, own_index).is_some_and(listed)
            || has(conditions::BET) && !self.bet_condition_met(capacity, side))
    }

    /// « Bet > N » / « Bet < N » : la mise de la carte, pillz gratuite comprise, fury non comptée.
    fn bet_condition_met(&self, capacity: &CompiledCapacity, side: usize) -> bool {
        let bet = self.fighters[side].pillz;
        if capacity.bet_under != 0 {
            bet < capacity.bet_under as i16
        } else {
            bet > capacity.bet_over as i16
        }
    }

    /// Un Oculus « Infiltrated » prend le bonus du clan adopté, s'il est listé sur sa carte ; sinon aucun.
    fn apply_infiltrated_bonus(&mut self, side: usize) {
        let hand = self.hand(side);
        let card = self.card(side);
        if !clan::is_infiltrated(card) {
            return;
        }
        let allowed = clan::infiltrable_clans(card);
        let bonus = clan::infiltrated_clan(hand)
            .filter(|&clan| allowed.is_none_or(|listed| listed >> clan & 1 == 1))
            .and_then(|clan| hand.iter().find(|mate| mate.clan == clan && mate.bonus.is_some()))
            .and_then(|source| source.bonus);
        self.fighters[side].slots[BONUS] = bonus;
    }

    /// L'ability « Team: X » du Leader, à appliquer à la carte jouée, si la main compte exactement un Leader (deux
    /// Leaders s'annulent ; un Oculus rallié au Leader compte comme un second).
    fn leader_team_capacity(&self, side: usize) -> Option<CompiledCapacity> {
        let hand = self.hand(side);
        let mut leaders = (0..hand.len()).filter(|&index| clan::clan_for_bonus(hand, index) == Some(clans::LEADER));
        let (Some(leader), None) = (leaders.next(), leaders.next()) else {
            return None;
        };
        let mut capacity = hand[leader].ability?;
        if capacity.conditions & bit(conditions::TEAM) == 0 {
            return None;
        }
        capacity.conditions &= !bit(conditions::TEAM);
        Some(capacity)
    }

    /// Modes de Leader lus avant les conditions : Counter-attack (son camp joue en second au premier round si un seul
    /// camp l'a) et Limitless (les maximums des abilities de l'équipe tombent, les minimums passent à 0).
    fn apply_leader_modes(&mut self) {
        let mut counter_attack = [false; 2];
        for side in SIDES {
            let fighter = &mut self.fighters[side];
            match fighter.slots[LEADER].map(|capacity| capacity.how) {
                Some(hows::COUNTER_ATTACK) => counter_attack[side] = true,
                Some(hows::LIMITLESS) => {
                    if let Some(ability) = &mut fighter.slots[ABILITY] {
                        if ability.borne != -1 {
                            ability.borne = if ability.value > 0 { -1 } else { 0 };
                        }
                    }
                }
                _ => continue,
            }
            fighter.slots[LEADER] = None;
        }
        if counter_attack[ALLY] != counter_attack[ENEMY] && self.nb_turn == 1 {
            self.ally_first = counter_attack[ENEMY];
        }
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

/// La valeur imprimée d'une stat (puissance ou dégâts), que lisent Copy, Exchange et Impose.
fn printed(card: &CompiledCard, stat: u32) -> i16 {
    if stat == POWER {
        card.power
    } else {
        card.damage
    }
}

fn hand(deck: &Deck, side: usize) -> &[CompiledCard] {
    if side == ALLY {
        &deck.ally
    } else {
        &deck.enemy
    }
}

/// Les camps touchés par une capacité de cible `target` portée par `side` : le sien, l'adverse, ou les deux.
fn affected_sides(target: u8, side: usize) -> impl Iterator<Item = usize> {
    let opp = ENEMY - side;
    let (first, second) = match target {
        targets::ALLY => (side, None),
        targets::ENEMY => (opp, None),
        _ => (side, Some(opp)),
    };
    std::iter::once(first).chain(second)
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
