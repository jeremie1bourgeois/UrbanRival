import { describe, expect, it } from "vitest";
import type { CatalogueCard } from "../../models/game.interface";
import { clanBonusStatus, randomDeck } from "../deck";

const card = (name: string, faction: string, levels = [3]): CatalogueCard => ({
	name,
	faction,
	starOff: 3,
	bonus: "bonus",
	bonus_supported: true,
	clan_image: "",
	levels: levels.map((stars) => ({ stars, power: 5, damage: 4, ability: "Power +2", ability_supported: true, image: "" })),
});
const catalogue = [
	card("Aamir", "All Stars"),
	card("Bhudd", "All Stars"),
	card("Ambre", "Leader"),
	card("Serafina", "Rescue"),
	card("Buf00n", "Oculus"),
	card("Kolos", "Nightmare", [2, 4, 5]),
];
const byName = new Map(catalogue.map((c) => [c.name, c]));

describe("clanBonusStatus", () => {
	it("activates a clan bonus with at least two cards of the clan", () => {
		const status = clanBonusStatus(
			[{ card_name: "Aamir", nb_stars: 3 }, { card_name: "Bhudd", nb_stars: 3 }, { card_name: "Serafina", nb_stars: 3 }, null],
			byName,
		);

		expect(status).toEqual([
			{ clan: "All Stars", count: 2, active: true },
			{ clan: "Rescue", count: 1, active: false },
		]);
	});

	it("counts an Oculus as a member of the majority clan and flags two Leaders", () => {
		const status = clanBonusStatus(
			[
				{ card_name: "Buf00n", nb_stars: 3 },
				{ card_name: "Serafina", nb_stars: 3 },
				{ card_name: "Ambre", nb_stars: 3 },
				{ card_name: "Ambre", nb_stars: 3 },
			],
			byName,
		);

		expect(status).toEqual([
			{ clan: "Rescue", count: 2, active: true },
			{ clan: "Leader", count: 2, active: false },
		]);
	});
});

describe("randomDeck", () => {
	it("draws four distinct cards at a playable level, reproducibly", () => {
		const rng = () => 0.42;
		const deck = randomDeck(catalogue, rng);

		expect(deck).toHaveLength(4);
		expect(new Set(deck.map((c) => c.card_name)).size).toBe(4);
		deck.forEach((slot) => expect(byName.get(slot.card_name)!.levels.map((l) => l.stars)).toContain(slot.nb_stars));
		expect(randomDeck(catalogue, rng)).toEqual(deck);
	});
});
