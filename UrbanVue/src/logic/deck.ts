import type { CatalogueCard, Deck, DeckCard, Situation } from "../models/game.interface";

export const DECK_SIZE = 4;

export type DeckSlots = (DeckCard | null)[];

export function emptySlots(): DeckSlots {
	return Array.from({ length: DECK_SIZE }, () => null);
}

/** Cartes dont le nom ou le clan contient la recherche (insensible à la casse) ; rien pour une recherche vide. */
export function filterCatalogue(catalogue: CatalogueCard[], query: string, limit = 30): CatalogueCard[] {
	const needle = query.trim().toLowerCase();
	if (needle === "") return [];
	return catalogue.filter((card) => card.name.toLowerCase().includes(needle) || card.faction.toLowerCase().includes(needle)).slice(0, limit);
}

export function isDeckComplete(slots: DeckSlots): slots is DeckCard[] {
	return slots.length === DECK_SIZE && slots.every((slot) => slot !== null);
}

/** Partie classique : 12 vies, 12 pillz, l'allié pose en premier. */
export const DEFAULT_SITUATION: Situation = { life: [12, 12], pillz: [12, 12], first: "player1" };

/** Modes connus ; sur le site le premier joueur du round 1 est toujours tiré au sort. Coliseum et Survivor : valeurs à la main. */
export const MODES: (Situation & { label: string })[] = [
	{ label: "Classic", life: [12, 12], pillz: [12, 12], first: "random" },
	{ label: "ELO", life: [14, 14], pillz: [12, 12], first: "random" },
	{ label: "Duel contre le bot", life: [15, 15], pillz: [12, 12], first: "random" },
];

export function toDeck(ally: DeckCard[], enemy: DeckCard[], situation: Situation = DEFAULT_SITUATION): Deck {
	return { player1: ally, player2: enemy, life: situation.life, pillz: situation.pillz, first: situation.first };
}

/** Message d'erreur si la situation n'est pas jouable (même règle que le backend : vies ≥ 1, pillz ≥ 0, entiers), sinon null. */
export function situationError(situation: Situation): string | null {
	if (!situation.life.every((value) => Number.isInteger(value) && value >= 1)) return "Les vies de départ doivent être des entiers ≥ 1.";
	if (!situation.pillz.every((value) => Number.isInteger(value) && value >= 0)) return "Les pillz de départ doivent être des entiers ≥ 0.";
	return null;
}

export interface ClanStatus {
	clan: string;
	count: number;
	/** Bonus de clan actif : au moins deux cartes du clan (un Oculus compte pour le clan majoritaire) ; jamais pour deux Leaders. */
	active: boolean;
}

/** Même règle que le backend (process_round.is_clan_bonus_active), pour l'afficher pendant la composition. */
export function clanBonusStatus(slots: DeckSlots, byName: Map<string, CatalogueCard>): ClanStatus[] {
	const factions = slots.flatMap((slot) => (slot ? [byName.get(slot.card_name)?.faction ?? "?"] : []));
	const counts = new Map<string, number>();
	for (const faction of factions) counts.set(faction, (counts.get(faction) ?? 0) + 1);
	const others = [...counts.entries()].filter(([clan]) => clan !== "Oculus" && clan !== "Leader").sort((a, b) => b[1] - a[1]);
	const oculus = counts.get("Oculus") ?? 0;
	const infiltrated = oculus > 0 && others.length > 0 && (others.length === 1 || others[0][1] > others[1][1]) ? others[0][0] : null;
	counts.delete("Oculus");
	if (infiltrated) counts.set(infiltrated, (counts.get(infiltrated) ?? 0) + oculus);
	return [...counts.entries()].map(([clan, count]) => ({ clan, count, active: clan === "Leader" ? false : count >= 2 }));
}

/** Quatre cartes distinctes à un niveau jouable ; `rng` renvoie un nombre dans [0, 1). */
export function randomDeck(catalogue: CatalogueCard[], rng: () => number = Math.random): DeckCard[] {
	const pool = catalogue.filter((card) => card.levels.length > 0);
	const deck: DeckCard[] = [];
	const used = new Set<number>();
	while (deck.length < DECK_SIZE && used.size < pool.length) {
		const index = Math.min(pool.length - 1, Math.floor(rng() * pool.length) + used.size) % pool.length;
		if (used.has(index)) continue;
		used.add(index);
		const card = pool[index];
		const level = card.levels[Math.min(card.levels.length - 1, Math.floor(rng() * card.levels.length))];
		deck.push({ card_name: card.name, nb_stars: level.stars });
	}
	return deck;
}
