import { describe, expect, it } from "vitest";
import { Card, Game, Player, hasUnsupportedPower } from "../game.interface";

const capacity = {
	target: "enemy",
	types: ["power", "damage"],
	value: -1,
	how: "equalizer",
	borne: 1,
	effect_conditions: ["courage"],
	lvl_priority: 0,
};

const rawCard = {
	name: "B Mappe Mt",
	faction: "All Stars",
	starOff: 5,
	stars: 5,
	power: 3,
	damage: 8,
	ability: capacity,
	bonus: null,
	ability_description: "Equalizer: -1 Opp Pow. & Dam., Min 1",
	bonus_description: "-2 Opp Power, Min 1",
	pillz_fight: 2,
	fury: true,
	attack: 6,
	played: true,
	power_fight: 1,
	damage_fight: 8,
	ability_fight: null,
	bonus_fight: null,
	win: false,
};

describe("Game", () => {
	it("keeps turn = false from the backend", () => {
		expect(new Game({ turn: false, ally: {}, enemy: {} }).turn).toBe(false);
	});
});

describe("Card", () => {
	it("maps the backend capacity shape (types, effect_conditions) and fury", () => {
		const card = new Card(rawCard);

		expect(card.ability?.types).toEqual(["power", "damage"]);
		expect(card.ability?.effect_conditions).toEqual(["courage"]);
		expect(card.bonus).toBeNull();
		expect(card.fury).toBe(true);
	});
});

describe("Card images", () => {
	it("maps the CDN image urls and defaults to empty strings", () => {
		expect(new Card({ ...rawCard, image: "https://cdn/x.png", clan_image: "https://cdn/c.png" })).toMatchObject({
			image: "https://cdn/x.png",
			clan_image: "https://cdn/c.png",
		});
		expect(new Card(rawCard)).toMatchObject({ image: "", clan_image: "" });
	});
});

describe("Player", () => {
	it("maps persistent effects", () => {
		const player = new Player({ name: "ally", life: 9, pillz: 7, cards: [], effect_list: [{ kind: "poison", value: 2, borne: 1 }] });

		expect(player.effect_list).toEqual([{ kind: "poison", value: 2, borne: 1 }]);
	});
});

describe("hasUnsupportedPower", () => {
	it.each([
		["Xantiax: -2 Life, Min. 0", true],
		["Ability at Level 3", false],
		["No Ability", false],
		["", false],
	])("without a parsed ability and description %s -> %s", (description, expected) => {
		const card = new Card({ ...rawCard, ability: null, ability_description: description });

		expect(hasUnsupportedPower(card, "ability")).toBe(expected);
	});

	it("is false when the ability is parsed", () => {
		expect(hasUnsupportedPower(new Card(rawCard), "ability")).toBe(false);
	});
});
