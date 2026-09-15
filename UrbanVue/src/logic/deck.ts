import type { CatalogueCard, Deck, DeckCard } from "../models/game.interface";

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

export function toDeck(ally: DeckCard[], enemy: DeckCard[]): Deck {
	return { player1: ally, player2: enemy };
}
