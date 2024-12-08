import axios from 'axios';
import { Game, RoundData } from '../models/game.interface.ts';

const apiClient = axios.create({
	baseURL: 'http://127.0.0.1:8000',
	headers: {
		'Content-Type': 'application/json',
	},
});

export const getInitGameTemplate = async (): Promise<{ status: string; game: Game; gameId: string }> => {
	try {
		const response = await apiClient.get('/init_game/template');
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
	roundData: RoundData,
	game: Game
): Promise<{ status: string; game: Game; state: any }> => {
	try {
		const response = await apiClient.post(`/process_round/${gameId}`, roundData);
		console.log('processGameRound response:', (response.data));
		console.log("game before", game);
		game.nb_turn = response.data.game.nb_turn || game.nb_turn;
		game.turn = response.data.game.turn || game.turn;
		game.ally = response.data.game.ally || game.ally;
		game.enemy = response.data.game.enemy || game.enemy;
		game.history = response.data.game.history || game.history;
		console.log("game after", game);
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