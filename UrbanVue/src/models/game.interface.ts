export class Capacity {
	target: string;
	type: string;
	value: number;
	how: string;
	borne: number;
	condition_effect: string;
	lvl_priority: number;

	constructor(data: any) {
		this.target = data.target || "";
		this.type = data.type || "";
		this.value = data.value || 0;
		this.how = data.how || "";
		this.borne = data.borne || 0;
		this.condition_effect = data.condition_effect || "";
		this.lvl_priority = data.lvl_priority || 0;
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
	bonus_description: string;
	ability_description: string;
	pillz_fight: number;
	attack: number;
	played: boolean;
	power_fight: number;
	damage_fight: number;
	ability_fight: Capacity | null;
	bonus_fight: Capacity | null;
	win: boolean;

	constructor(data: any) {
		this.name = data.name || "";
		this.faction = data.faction || "";
		this.starOff = data.starOff || 0;
		this.bonus = data.bonus ? new Capacity(data.bonus) : null;
		this.stars = data.stars || 0;
		this.power = data.power || 0;
		this.damage = data.damage || 0;
		this.ability = data.ability ? new Capacity(data.ability) : null;
		this.bonus_description = data.bonus_description || "";
		this.ability_description = data.ability_description || "";
		this.pillz_fight = data.pillz_fight || 0;
		this.attack = data.attack || 0;
		this.played = data.played || false;
		this.power_fight = data.power_fight || 0;
		this.damage_fight = data.damage_fight || 0;
		this.ability_fight = data.ability_fight ? new Capacity(data.ability_fight) : null;
		this.bonus_fight = data.bonus_fight ? new Capacity(data.bonus_fight) : null;
		this.win = data.win || false;
	}
}

export class Player {
	name: string;
	life: number;
	pillz: number;
	cards: Card[];
	effect_list: [any, number, number][];

	constructor(data: any) {
		this.name = data.name || "";
		this.life = data.life || 0;
		this.pillz = data.pillz || 0;
		this.cards = (data.cards || []).map((card: any) => new Card(card));
		this.effect_list = data.effect_list || [];
	}
}

export class Game {
	nb_turn: number;
	turn: boolean;
	ally: Player;
	enemy: Player;
	history: string[];

	constructor(data: any) {
		this.nb_turn = data.nb_turn || 0;
		this.turn = data.turn || true;
		this.ally = new Player(data.ally || {});
		this.enemy = new Player(data.enemy || {});
		this.history = data.history || [];
	}
}

export class RoundData {
	player1_card_index: number;
	player1_pillz: number;
	player1_fury: boolean;
	player2_card_index: number;
	player2_pillz: number;
	player2_fury: boolean;
}
