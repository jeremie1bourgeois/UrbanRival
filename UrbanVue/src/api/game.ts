import axios from 'axios';
import { Game } from '../models/game.interface.ts';

const apiClient = axios.create({
	baseURL: 'http://127.0.0.1:8000',
	headers: {
		'Content-Type': 'application/json',
	},
});

export const getInitGameTemplate = async (): Promise<{ status: string; game: Game; gameId: string }> => {
	try {
		const response = await apiClient.get('/init_game/template');
		console.log('Init game template:', JSON.stringify(response.data));
		return {
			status: response.data.status,
			game: new Game(response.data.game),
			gameId: response.data.game_id,
		};
	} catch (error) {
		console.error('Error fetching init game template:', error);
		throw error;
	}
};

// Fonction pour traiter un round
export const processGameRound = async (
	gameId: string,
	roundData: {
		player1_card_index: number;
		player1_pillz: number;
		player1_fury: boolean;
		player2_card_index: number;
		player2_pillz: number;
		player2_fury: boolean;
	}
): Promise<{ status: string; game: Game; state: any }> => {
	try {
		const response = await apiClient.post(`/process_round/${gameId}`, roundData);
		console.log('Round processed:', response.data);
		return {
			status: response.data.status,
			game: new Game(response.data.game),
			state: response.data.state,
		};
	} catch (error) {
		console.error('Error processing game round:', error);
		throw error;
	}
};