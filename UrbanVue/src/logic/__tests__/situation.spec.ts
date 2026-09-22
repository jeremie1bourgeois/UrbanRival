import { describe, expect, it } from "vitest";
import { DEFAULT_SITUATION, MODES, situationError, toDeck } from "../deck";

const ally = [
	{ card_name: "Aamir", nb_stars: 3 },
	{ card_name: "Bhudd", nb_stars: 3 },
	{ card_name: "Aamir", nb_stars: 2 },
	{ card_name: "Bhudd", nb_stars: 1 },
];
const enemy = [
	{ card_name: "Serafina", nb_stars: 5 },
	{ card_name: "Ambre", nb_stars: 3 },
	{ card_name: "Serafina", nb_stars: 4 },
	{ card_name: "Ambre", nb_stars: 2 },
];

describe("situation de départ (ce qui distingue un mode de jeu)", () => {
	it("is part of the payload of POST /init_game/, player 1 being the ally", () => {
		expect(toDeck(ally, enemy, { life: [16, 12], pillz: [8, 12], first: "random" })).toEqual({
			player1: ally,
			player2: enemy,
			life: [16, 12],
			pillz: [8, 12],
			first: "random",
		});
	});

	it("defaults to the classic 12 lives, 12 pillz, ally first", () => {
		expect(DEFAULT_SITUATION).toEqual({ life: [12, 12], pillz: [12, 12], first: "player1" });
		expect(toDeck(ally, enemy)).toMatchObject(DEFAULT_SITUATION);
	});

	it("offers the known modes as presets, first player drawn at random as on the site", () => {
		expect(MODES.map((mode) => [mode.label, ...mode.life, ...mode.pillz, mode.first])).toEqual([
			["Classic", 12, 12, 12, 12, "random"],
			["ELO", 14, 14, 12, 12, "random"],
			["Duel contre le bot", 15, 15, 12, 12, "random"],
		]);
	});

	it("rejects lives below 1, negative pillz and non-integers", () => {
		expect(situationError({ life: [12, 12], pillz: [12, 12], first: "player1" })).toBeNull();
		expect(situationError({ life: [0, 12], pillz: [12, 12], first: "player1" })).toMatch(/vies/);
		expect(situationError({ life: [12, 12], pillz: [12, -1], first: "player1" })).toMatch(/pillz/);
		expect(situationError({ life: [12.5, 12], pillz: [12, 12], first: "player1" })).toMatch(/vies/);
		expect(situationError({ life: [12, 12], pillz: [Number.NaN, 12], first: "player1" })).toMatch(/pillz/);
	});
});
