import type { DeckSlots } from "./deck";

const KEY = "urbanrival.decks";

export interface SavedDecks {
	ally: DeckSlots;
	enemy: DeckSlots;
}

/** Derniers decks composés (localStorage) ; null si absents ou illisibles. */
export function loadSavedDecks(): SavedDecks | null {
	try {
		const raw = localStorage.getItem(KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed?.ally) || !Array.isArray(parsed?.enemy)) return null;
		return { ally: parsed.ally, enemy: parsed.enemy };
	} catch {
		return null;
	}
}

export function saveDecks(decks: SavedDecks): void {
	try {
		localStorage.setItem(KEY, JSON.stringify(decks));
	} catch {
		// stockage indisponible : on ignore
	}
}
