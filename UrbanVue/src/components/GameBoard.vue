<script setup lang="ts">
import { ref } from "vue";
import { Game, RoundData } from "../models/game.interface.ts";
import { getInitGameTemplate, processGameRound } from "../api/game";
import Card from "./Card.vue";

const game = ref<Game | null>(null);
const status = ref<string | null>(null);
const gameId = ref<string>("");
const turn = ref<boolean>(game.value?.turn || false);
const roundData = ref<RoundData>({
	player1_card_index: -1,
	player1_pillz: -1,
	player1_fury: false,
	player2_card_index: -1,
	player2_pillz: -1,
	player2_fury: false,
});

const fetchGame = async () => {
	try {
		const { status: fetchedStatus, game: fetchedGame, gameId: fetchedGameId } = await getInitGameTemplate();
		status.value = fetchedStatus;
		game.value = fetchedGame;
		gameId.value = fetchedGameId;
	} catch (error) {
		console.error("Error loading game:", error);
	}
};

const handleCombat = (pillz: number, isFury: boolean, index: number) => {
	if (turn.value) {
		roundData.value.player1_card_index = index;
		roundData.value.player1_pillz = pillz;
		roundData.value.player1_fury = isFury;
	} else {
		roundData.value.player2_card_index = index;
		roundData.value.player2_pillz = pillz;
		roundData.value.player2_fury = isFury;
	}
	if (roundData.value.player1_card_index !== -1 && roundData.value.player2_card_index !== -1 && game.value) {
		processGameRound(gameId.value, roundData.value, game.value).then((response) => {
			game.value = response.game;
			roundData.value = {
				player1_card_index: -1,
				player1_pillz: -1,
				player1_fury: false,
				player2_card_index: -1,
				player2_pillz: -1,
				player2_fury: false,
			};
		});
	} else {
		turn.value = !turn.value;
	}
};
</script>

<template>
	<div class="flex justify-center items-center bg-gray-900">
		<div class="text-white">
			<button @click="fetchGame" class="bg-blue-500 text-white px-4 py-2 rounded shadow hover:bg-blue-600 mb-4">Charger la game</button>
			<p><strong>Status:</strong> {{ status }}</p>
			<p><strong>Game ID:</strong> {{ gameId }}</p>
		</div>

		<div id="GameBoard" class="flex flex-col items-center gap-8 bg-gray-800 text-white rounded-xl" style="transform-origin: top left" v-if="game">
			<div class="w-full flex flex-col items-center p-4 rounded-xl" :class="{ 'bg-gradient-to-b from-blue-800 to-gray-800': !turn }">
				<div class="flex w-full justify-start space-x-10 pb-4">
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ game.enemy.name }}</h2>
					<p class="text-sm text-gray-300 mt-2">Life: {{ game.enemy.life }} | Pillz: {{ game.enemy.pillz }}</p>
				</div>
				<div class="flex justify-center space-x-3">
					<Card
						v-for="(card, index) in game.enemy.cards"
						:key="'enemy-' + index"
						:card="card"
						:pillz="game.enemy.pillz"
						:turn="!turn"
						@combat="(pillz, isFury) => handleCombat(pillz, isFury, index)"
					/>
				</div>
			</div>
			<div class="w-[95%] border-t border-gray-600 my-4"></div>
			<div class="w-full flex flex-col items-center p-4 rounded-xl" :class="{ 'bg-gradient-to-b from-gray-800 to-blue-900': turn }">
				<div class="flex justify-center space-x-3">
					<Card
						v-for="(card, index) in game.ally.cards"
						:key="'ally-' + index"
						:card="card"
						:pillz="game.ally.pillz"
						:turn="turn"
						@combat="(pillz, isFury) => handleCombat(pillz, isFury, index)"
					/>
				</div>
				<div class="flex w-full justify-end space-x-10 pt-4">
					<p class="text-sm text-gray-300 mt-2">Life: {{ game.ally.life }} | Pillz: {{ game.ally.pillz }}</p>
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ game.ally.name }}</h2>
				</div>
			</div>
		</div>
	</div>
</template>
