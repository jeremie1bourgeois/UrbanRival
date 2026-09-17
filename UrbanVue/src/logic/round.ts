import type { Game, RoundData } from "../models/game.interface";

export type Side = "ally" | "enemy";

export interface Pick {
	index: number;
	pillz: number;
	fury: boolean;
}

/** Enchaîne les deux choix d'un round dans l'ordre imposé par le backend (game.turn) et produit le RoundData. */
export class RoundPicker {
	private readonly order: Side[];
	private readonly picks: Partial<Record<Side, Pick>> = {};

	constructor(game: Game) {
		this.order = game.turn ? ["ally", "enemy"] : ["enemy", "ally"];
	}

	get current(): Side | null {
		return this.order.find((side) => this.picks[side] === undefined) ?? null;
	}

	/**
	 * Carte posée par le premier joueur, une fois qu'il a choisi : le second la voit avant de jouer
	 * (règle Urban Rivals — la carte est visible, la mise en pillz non). Null tant que personne n'a joué.
	 */
	get revealed(): { side: Side; index: number } | null {
		const [first] = this.order;
		const pick = this.picks[first];
		return pick === undefined ? null : { side: first, index: pick.index };
	}

	/** Enregistre le choix du joueur courant ; renvoie le RoundData quand les deux joueurs ont choisi. */
	pick(pick: Pick): RoundData | null {
		const side = this.current;
		if (side === null) return null;
		this.picks[side] = pick;
		const ally = this.picks.ally;
		const enemy = this.picks.enemy;
		if (ally === undefined || enemy === undefined) return null;
		return {
			player1_card_index: ally.index,
			player1_pillz: ally.pillz,
			player1_fury: ally.fury,
			player2_card_index: enemy.index,
			player2_pillz: enemy.pillz,
			player2_fury: enemy.fury,
		};
	}
}
