import axios from "axios";
import { Game, type CatalogueCard, type Deck, type GameState, type RoundData } from "../models/game.interface";

const apiClient = axios.create({
	baseURL: "http://127.0.0.1:8000",
	headers: { "Content-Type": "application/json" },
});

export type Opponent = "human" | "random" | "heuristic";

export const OPPONENT_LABELS: Record<Opponent, string> = {
	human: "Deux joueurs (même écran)",
	random: "Ordinateur — aléatoire",
	heuristic: "Ordinateur — heuristique",
};

export interface StartedGame {
	game: Game;
	gameId: string;
	opponent: Opponent;
}

export interface AiPick {
	card_index: number;
	pillz: number;
	fury: boolean;
}

export async function getCatalogue(): Promise<CatalogueCard[]> {
	const response = await apiClient.get<CatalogueCard[]>("/cards");
	return response.data;
}

export async function getInitGameTemplate(opponent: Opponent = "human"): Promise<StartedGame> {
	const response = await apiClient.get("/init_game/template");
	return { game: new Game(response.data.game), gameId: String(response.data.game_id), opponent };
}

export async function initGame(deck: Deck, opponent: Opponent = "human"): Promise<StartedGame> {
	const response = await apiClient.post("/init_game/", deck);
	return { game: new Game(response.data.game), gameId: String(response.data.game_id), opponent };
}

/** Choix de l'ordinateur pour le camp ennemi, sans jouer le round. */
export async function aiPick(gameId: string, strategy: Exclude<Opponent, "human">): Promise<AiPick> {
	const response = await apiClient.post<AiPick>(`/ai_pick/${gameId}`, { strategy, side: "enemy" });
	return response.data;
}

export async function processGameRound(gameId: string, roundData: RoundData): Promise<{ game: Game; state: GameState }> {
	const response = await apiClient.post(`/process_round/${gameId}`, roundData);
	return { game: new Game(response.data.game), state: response.data.state };
}

/** Fige un round en fixture de régression ; `nbTurn` est l'état d'arrivée du round (défaut : le dernier joué). */
export async function savePlayForTest(gameId: string, nbTurn?: number): Promise<void> {
	await apiClient.get("/save_for_test", { params: { game_id: gameId, ...(nbTurn === undefined ? {} : { nb_turn: nbTurn }) } });
}

/** Message d'erreur renvoyé par le backend (detail) ou message générique. */
export function errorMessage(error: unknown): string {
	if (axios.isAxiosError(error)) {
		const detail = error.response?.data?.detail;
		if (typeof detail === "string") return detail;
		if (error.response === undefined) return "Backend injoignable (http://127.0.0.1:8000).";
	}
	return error instanceof Error ? error.message : String(error);
}
