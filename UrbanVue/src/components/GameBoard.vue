<script setup lang="ts">
import { ref } from "vue";
import { Game, RoundData } from "../models/game.interface.ts";
import { getInitGameTemplate, processGameRound } from "../api/game";
import Card from "./Card.vue";

// Références pour les données de la game
const game = ref<Game | null>(null);
const status = ref<string | null>(null);
const gameId = ref<string>("");
const maxPillz = ref<number>(12); // Nombre maximal de pillz disponibles (peut varier selon la logique)
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
		// Déstructuration des valeurs retournées par la fonction
		const { status: fetchedStatus, game: fetchedGame, gameId: fetchedGameId } = await getInitGameTemplate();
		status.value = fetchedStatus;
		game.value = fetchedGame;
		gameId.value = fetchedGameId;
	} catch (error) {
		console.error("Error loading game:", error);
	}
};

const handleCombat = (pillz: number, isFury: boolean, index: number) => {
	console.log("Combat:", pillz, isFury, index);
	if (turn.value) {
		roundData.value.player1_card_index = index;
		roundData.value.player1_pillz = pillz;
		roundData.value.player1_fury = isFury;
	} else {
		roundData.value.player2_card_index = index;
		roundData.value.player2_pillz = pillz;
		roundData.value.player2_fury = isFury;
	}
	console.log("Round data:", roundData.value);
	if (roundData.value.player1_card_index !== -1 && roundData.value.player2_card_index !== -1) {
		console.log("Round data:", roundData.value);
		processGameRound(gameId.value, roundData.value).then((response) => {
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
		console.log("Waiting for other player...");
		turn.value = !turn.value;
	}
};
</script>

<template>
	<div class="flex flex-col justify-center items-center bg-gray-900">
		<button @click="fetchGame" class="bg-blue-500 text-white px-4 py-2 rounded shadow hover:bg-blue-600 mb-4">Charger la game</button>

		<div v-if="status" class="text-white mb-4">
			<p><strong>Status:</strong> {{ status }}</p>
			<p><strong>Game ID:</strong> {{ gameId }}</p>
		</div>

		<div
			id="GameBoard"
			class="flex flex-col items-center gap-8 bg-gray-800 text-white p-4 rounded-md"
			style="transform-origin: top left"
			v-if="game"
		>
			<div class="w-full flex flex-col items-center">
				<div class="flex w-full justify-start space-x-10 pb-4">
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ game.enemy.name }}</h2>
					<p class="text-sm text-gray-300 mt-2">Life: {{ game.enemy.life }} | Pillz: {{ game.enemy.pillz }}</p>
				</div>
				<div class="flex flex-wrap justify-center gap-4">
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
			<div class="w-full border-t border-gray-600 my-4"></div>
			<div class="w-full flex flex-col items-center">
				<div class="flex flex-wrap justify-center gap-4">
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
