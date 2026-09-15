import { describe, expect, it } from "vitest";
import type { CatalogueCard } from "../../models/game.interface";
import { emptySlots, filterCatalogue, isDeckComplete, toDeck } from "../deck";

const card = (name: string, faction: string): CatalogueCard => ({
	name,
	faction,
	starOff: 3,
	bonus: "-2 Opp Power, Min 1",
	bonus_supported: true,
	levels: [{ stars: 3, power: 5, damage: 4, ability: "Power +2", ability_supported: true }],
});
const catalogue = [card("Aamir", "All Stars"), card("Ambre", "Leader"), card("Bhudd", "All Stars"), card("Serafina", "Rescue")];

describe("filterCatalogue", () => {
	it("matches the name or the clan, case-insensitively", () => {
		expect(filterCatalogue(catalogue, "all st").map((c) => c.name)).toEqual(["Aamir", "Bhudd"]);
		expect(filterCatalogue(catalogue, "SERA").map((c) => c.name)).toEqual(["Serafina"]);
	});

	it("returns nothing for an empty query and caps the result size", () => {
		expect(filterCatalogue(catalogue, "  ")).toEqual([]);
		expect(filterCatalogue(catalogue, "a", 2)).toHaveLength(2);
	});
});

describe("deck slots", () => {
	it("is complete only when the four slots are filled", () => {
		const slots = emptySlots();
		expect(isDeckComplete(slots)).toBe(false);
		slots[0] = slots[1] = slots[2] = { card_name: "Aamir", nb_stars: 3 };
		expect(isDeckComplete(slots)).toBe(false);
		slots[3] = { card_name: "Bhudd", nb_stars: 3 };
		expect(isDeckComplete(slots)).toBe(true);
	});

	it("builds the payload of POST /init_game/", () => {
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

		expect(toDeck(ally, enemy)).toEqual({ player1: ally, player2: enemy });
	});
});
