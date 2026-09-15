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
});
