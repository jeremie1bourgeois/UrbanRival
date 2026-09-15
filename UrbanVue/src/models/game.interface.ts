// Miroir des objets sérialisés par le backend (Game.to_dict / Card.to_dict / Capacity.to_dict).

export type CapacityKind = "ability" | "bonus";

export interface RoundRecord {
	ally: { card_index: number | null; win: boolean };
	enemy: { card_index: number | null; win: boolean };
}

// Formes brutes telles que renvoyées par l'API (tout est optionnel : les constructeurs posent les défauts).
export interface RawCapacity {
	target?: string;
	types?: string[];
	value?: number;
	how?: string;
	borne?: number;
	effect_conditions?: string[];
	lvl_priority?: number;
}

export interface RawPersistentEffect {
	kind?: string;
	value?: number;
	borne?: number;
}

export interface RawCard {
	name?: string;
	faction?: string;
	starOff?: number;
	bonus?: RawCapacity | null;
	stars?: number;
	power?: number;
	damage?: number;
	ability?: RawCapacity | null;
	image?: string;
	clan_image?: string;
	bonus_description?: string;
	ability_description?: string;
	pillz_fight?: number;
	fury?: boolean;
	attack?: number;
	played?: boolean | number;
	power_fight?: number;
	damage_fight?: number;
	ability_fight?: RawCapacity | null;
	bonus_fight?: RawCapacity | null;
	win?: boolean;
}

export interface RawPlayer {
	name?: string;
	life?: number;
	pillz?: number;
	cards?: RawCard[];
	effect_list?: RawPersistentEffect[];
}

export interface RawGame {
	nb_turn?: number;
	turn?: boolean;
	ally?: RawPlayer;
	enemy?: RawPlayer;
	history?: RoundRecord[];
}

export class Capacity {
	target: string;
	types: string[];
	value: number;
	how: string;
	borne: number;
	effect_conditions: string[];
	lvl_priority: number;

	constructor(data: RawCapacity) {
		this.target = data.target ?? "";
		this.types = data.types ?? [];
		this.value = data.value ?? 0;
		this.how = data.how ?? "";
		this.borne = data.borne ?? -1;
		this.effect_conditions = data.effect_conditions ?? [];
		this.lvl_priority = data.lvl_priority ?? 0;
	}
}

export class PersistentEffect {
	kind: string;
	value: number;
	borne: number;

	constructor(data: RawPersistentEffect) {
		this.kind = data.kind ?? "";
		this.value = data.value ?? 0;
		this.borne = data.borne ?? -1;
	}
}

export class Card {
	name: string;
	faction: string;
	starOff: number;
	bonus: Capacity | null;
	stars: number;
	power: number;
	damage: number;
	ability: Capacity | null;
	/** Illustration de la carte à ce niveau (URL CDN) ; vide pour les anciennes données. */
	image: string;
	clan_image: string;
	bonus_description: string;
	ability_description: string;
	pillz_fight: number;
	fury: boolean;
	attack: number;
	played: boolean;
	power_fight: number;
	damage_fight: number;
	ability_fight: Capacity | null;
	bonus_fight: Capacity | null;
	win: boolean;

	constructor(data: RawCard) {
		this.name = data.name ?? "";
		this.faction = data.faction ?? "";
		this.starOff = data.starOff ?? 0;
		this.bonus = data.bonus ? new Capacity(data.bonus) : null;
		this.stars = data.stars ?? 0;
		this.power = data.power ?? 0;
		this.damage = data.damage ?? 0;
		this.ability = data.ability ? new Capacity(data.ability) : null;
		this.image = data.image ?? "";
		this.clan_image = data.clan_image ?? "";
		this.bonus_description = data.bonus_description ?? "";
		this.ability_description = data.ability_description ?? "";
		this.pillz_fight = data.pillz_fight ?? 0;
		this.fury = data.fury ?? false;
		this.attack = data.attack ?? 0;
		this.played = Boolean(data.played);
		this.power_fight = data.power_fight ?? 0;
		this.damage_fight = data.damage_fight ?? 0;
		this.ability_fight = data.ability_fight ? new Capacity(data.ability_fight) : null;
		this.bonus_fight = data.bonus_fight ? new Capacity(data.bonus_fight) : null;
		this.win = data.win ?? false;
	}
}

/** Vrai si la carte porte un pouvoir que le moteur ne sait pas (encore) jouer : texte présent mais aucune capacité structurée. */
export function hasUnsupportedPower(card: Card, kind: CapacityKind): boolean {
	const parsed = kind === "ability" ? card.ability : card.bonus;
	const description = (kind === "ability" ? card.ability_description : card.bonus_description).trim();
	if (parsed !== null || description === "") return false;
	return !/^(no ability|ability at level \d+)$/i.test(description);
}

export class Player {
	name: string;
	life: number;
	pillz: number;
	cards: Card[];
	effect_list: PersistentEffect[];

	constructor(data: RawPlayer) {
		this.name = data.name ?? "";
		this.life = data.life ?? 0;
		this.pillz = data.pillz ?? 0;
		this.cards = (data.cards ?? []).map((card) => new Card(card));
		this.effect_list = (data.effect_list ?? []).map((effect) => new PersistentEffect(effect));
	}
}

export class Game {
	nb_turn: number;
	/** true : l'allié joue en premier ce round ; false : l'ennemi. */
	turn: boolean;
	ally: Player;
	enemy: Player;
	history: RoundRecord[];

	constructor(data: RawGame) {
		this.nb_turn = data.nb_turn ?? 0;
		this.turn = data.turn ?? true;
		this.ally = new Player(data.ally ?? {});
		this.enemy = new Player(data.enemy ?? {});
		this.history = data.history ?? [];
	}
}

export type GameState = "Ally Wins" | "Enemy Wins" | "Draw" | "Game Not Finished";

export interface RoundData {
	player1_card_index: number;
	player1_pillz: number;
	player1_fury: boolean;
	player2_card_index: number;
	player2_pillz: number;
	player2_fury: boolean;
}

// --- Catalogue (GET /cards) et composition de deck (POST /init_game/) ---

export interface CatalogueLevel {
	stars: number;
	power: number;
	damage: number;
	ability: string;
	ability_supported: boolean;
	image: string;
}

export interface CatalogueCard {
	name: string;
	faction: string;
	starOff: number;
	bonus: string;
	bonus_supported: boolean;
	clan_image: string;
	levels: CatalogueLevel[];
}

export interface DeckCard {
	card_name: string;
	nb_stars: number;
}

export interface Deck {
	player1: DeckCard[];
	player2: DeckCard[];
}
