import { beforeEach, describe, expect, it } from "vitest";
import { loadSavedDecks, saveDecks } from "../storage";

describe("deck storage", () => {
	beforeEach(() => localStorage.clear());

	it("round-trips the two decks and returns null when nothing is saved", () => {
		expect(loadSavedDecks()).toBeNull();
		const decks = {
			ally: [{ card_name: "Aamir", nb_stars: 3 }, null, null, null],
			enemy: [null, null, null, { card_name: "Azel", nb_stars: 5 }],
		};

		saveDecks(decks);

		expect(loadSavedDecks()).toEqual(decks);
	});

	it("ignores corrupted storage", () => {
		localStorage.setItem("urbanrival.decks", "{not json");

		expect(loadSavedDecks()).toBeNull();
	});
});
