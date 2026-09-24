import { describe, expect, it } from "vitest";
import { API_BASE_URL, cardImageUrl } from "../backend";

describe("cardImageUrl", () => {
	it("route une illustration du CDN vers le cache du backend", () => {
		expect(cardImageUrl("https://s.acdn.ur-img.com/characters/d042e419c1a379aefc991af5b49fecd1.png")).toBe(
			`${API_BASE_URL}/card_image/d042e419c1a379aefc991af5b49fecd1.png`,
		);
	});

	it("rend une chaîne vide quand la carte n'a pas d'image", () => {
		expect(cardImageUrl("")).toBe("");
	});
});
