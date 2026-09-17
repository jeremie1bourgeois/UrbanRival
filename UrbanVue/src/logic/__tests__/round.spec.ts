import { describe, expect, it } from "vitest";
import { Game } from "../../models/game.interface";
import { RoundPicker } from "../round";

describe("RoundPicker", () => {
	it("lets the ally pick first when game.turn is true, then the enemy, then submits", () => {
		const picker = new RoundPicker(new Game({ turn: true, ally: {}, enemy: {} }));

		expect(picker.current).toBe("ally");
		expect(picker.pick({ index: 2, pillz: 3, fury: false })).toBeNull();
		expect(picker.current).toBe("enemy");
		expect(picker.pick({ index: 0, pillz: 1, fury: true })).toEqual({
			player1_card_index: 2,
			player1_pillz: 3,
			player1_fury: false,
			player2_card_index: 0,
			player2_pillz: 1,
			player2_fury: true,
		});
	});

	it("lets the enemy pick first when game.turn is false", () => {
		const picker = new RoundPicker(new Game({ turn: false, ally: {}, enemy: {} }));

		expect(picker.current).toBe("enemy");
		picker.pick({ index: 1, pillz: 2, fury: false });
		expect(picker.current).toBe("ally");
	});

	// Règle Urban Rivals : le second joueur voit la carte posée par le premier, jamais ses pillz.
	it("reveals the first player's card to the second one, and nothing before", () => {
		const picker = new RoundPicker(new Game({ turn: false, ally: {}, enemy: {} }));

		expect(picker.revealed).toBeNull();
		picker.pick({ index: 3, pillz: 7, fury: true });

		expect(picker.revealed).toEqual({ side: "enemy", index: 3 });
	});

	it("keeps the second player's card hidden from the first one", () => {
		const picker = new RoundPicker(new Game({ turn: true, ally: {}, enemy: {} }));

		picker.pick({ index: 1, pillz: 2, fury: false });

		expect(picker.revealed).toEqual({ side: "ally", index: 1 });
	});
});
