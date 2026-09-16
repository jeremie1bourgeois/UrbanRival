import type { Game } from "../models/game.interface";

export interface PlayedCardSummary {
	name: string;
	/** Pillz misées (pillz_fight - 1). */
	pillz: number;
	fury: boolean;
	attack: number;
	power: number;
	damage: number;
	win: boolean;
}

export interface RoundSummary {
	round: number;
	ally: PlayedCardSummary;
	enemy: PlayedCardSummary;
	lifeAfter: { ally: number; enemy: number };
}

/** Résume chaque round joué à partir des états successifs de la partie (l'état d'après porte les cartes jouées). */
export function roundSummaries(states: Game[]): RoundSummary[] {
	const summaries: RoundSummary[] = [];
	for (let i = 1; i < states.length; i++) {
		const after = states[i];
		const record = after.history[after.history.length - 1];
		if (!record || record.ally.card_index === null || record.enemy.card_index === null) continue;
		const ally = after.ally.cards[record.ally.card_index];
		const enemy = after.enemy.cards[record.enemy.card_index];
		const summary = (card: typeof ally, win: boolean): PlayedCardSummary => ({
			name: card.name,
			pillz: Math.max(0, card.pillz_fight - 1),
			fury: card.fury,
			attack: card.attack,
			power: card.power_fight,
			damage: card.damage_fight,
			win,
		});
		summaries.push({
			round: states[i - 1].nb_turn,
			ally: summary(ally, record.ally.win),
			enemy: summary(enemy, record.enemy.win),
			lifeAfter: { ally: after.ally.life, enemy: after.enemy.life },
		});
	}
	return summaries;
}
