import axios from "axios";
import { API_BASE_URL } from "./backend";
import { Game, type CatalogueCard, type Deck, type GameState, type RoundData } from "../models/game.interface";

const apiClient = axios.create({
	baseURL: API_BASE_URL,
	headers: { "Content-Type": "application/json" },
});

export interface StartedGame {
	game: Game;
	gameId: string;
}

export async function getCatalogue(): Promise<CatalogueCard[]> {
	const response = await apiClient.get<CatalogueCard[]>("/cards");
	return response.data;
}

export async function getInitGameTemplate(): Promise<StartedGame> {
	const response = await apiClient.get("/init_game/template");
	return { game: new Game(response.data.game), gameId: String(response.data.game_id) };
}

export async function initGame(deck: Deck): Promise<StartedGame> {
	const response = await apiClient.post("/init_game/", deck);
	return { game: new Game(response.data.game), gameId: String(response.data.game_id) };
}

export async function processGameRound(gameId: string, roundData: RoundData): Promise<{ game: Game; state: GameState }> {
	const response = await apiClient.post(`/process_round/${gameId}`, roundData);
	return { game: new Game(response.data.game), state: response.data.state };
}

export async function savePlayForTest(gameId: string): Promise<void> {
	await apiClient.get("/save_for_test", { params: { game_id: gameId } });
}

/** Message d'erreur renvoyé par le backend (detail) ou message générique. */
export function errorMessage(error: unknown): string {
	if (axios.isAxiosError(error)) {
		const detail = error.response?.data?.detail;
		if (typeof detail === "string") return detail;
		if (error.response === undefined) return `Backend injoignable (${API_BASE_URL}).`;
	}
	return error instanceof Error ? error.message : String(error);
}
