import { describe, expect, it } from "vitest";
import { Game } from "../../models/game.interface";
import { roundSummaries } from "../history";

const state = (nb_turn: number, allyLife: number, enemyLife: number, history: object[], allyCards: object[], enemyCards: object[]) =>
	new Game({
		nb_turn,
		turn: true,
		ally: { name: "ally", life: allyLife, pillz: 9, cards: allyCards },
		enemy: { name: "enemy", life: enemyLife, pillz: 10, cards: enemyCards },
		history,
	});

const played = (name: string, extra: object) => ({ name, power: 5, damage: 3, played: true, ...extra });

describe("roundSummaries", () => {
	it("pairs consecutive states into one summary per round", () => {
		const before = state(1, 12, 12, [], [{ name: "Aamir" }, { name: "Bhudd" }], [{ name: "Azel" }, { name: "Artus" }]);
		const after = state(
			2,
			8,
			12,
			[{ ally: { card_index: 1, win: false }, enemy: { card_index: 0, win: true } }],
			[{ name: "Aamir" }, played("Bhudd", { pillz_fight: 3, attack: 9, fury: false, power_fight: 3, damage_fight: 2, win: false })],
			[played("Azel", { pillz_fight: 8, attack: 56, fury: true, power_fight: 7, damage_fight: 4, win: true }), { name: "Artus" }],
		);

		expect(roundSummaries([before, after])).toEqual([
			{
				round: 1,
				ally: { name: "Bhudd", pillz: 2, fury: false, attack: 9, power: 3, damage: 2, win: false },
				enemy: { name: "Azel", pillz: 7, fury: true, attack: 56, power: 7, damage: 4, win: true },
				lifeAfter: { ally: 8, enemy: 12 },
				log: [],
			},
		]);
	});

	it("carries the round log when the backend provides one", () => {
		const log = [{ side: "ally", card: "Bhudd", source: "attaque", text: "Bhudd : attaque = 3 × 3 pillz = 9" }];
		const before = state(1, 12, 12, [], [{ name: "Bhudd" }], [{ name: "Azel" }]);
		const after = state(
			2,
			8,
			12,
			[{ ally: { card_index: 0, win: false }, enemy: { card_index: 0, win: true }, log }],
			[played("Bhudd", { pillz_fight: 3, attack: 9, fury: false, power_fight: 3, damage_fight: 2, win: false })],
			[played("Azel", { pillz_fight: 8, attack: 56, fury: true, power_fight: 7, damage_fight: 4, win: true })],
		);

		expect(roundSummaries([before, after])[0].log).toEqual(log);
	});

	it("defaults the log to an empty list for older saves", () => {
		const before = state(1, 12, 12, [], [{ name: "Bhudd" }], [{ name: "Azel" }]);
		const after = state(
			2,
			8,
			12,
			[{ ally: { card_index: 0, win: false }, enemy: { card_index: 0, win: true } }],
			[played("Bhudd", { pillz_fight: 3, attack: 9, fury: false, power_fight: 3, damage_fight: 2, win: false })],
			[played("Azel", { pillz_fight: 8, attack: 56, fury: true, power_fight: 7, damage_fight: 4, win: true })],
		);

		expect(roundSummaries([before, after])[0].log).toEqual([]);
	});

	it("is empty with a single state", () => {
		expect(roundSummaries([state(1, 12, 12, [], [], [])])).toEqual([]);
	});
});
