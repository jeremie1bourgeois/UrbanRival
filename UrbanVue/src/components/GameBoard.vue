<script setup lang="ts">
import { ref } from "vue";
import { Game } from "../models/game.interface.ts"; // Assurez-vous que le chemin est correct
import { getInitGameTemplate } from "../api/game"; // Assurez-vous que le chemin est correct
import Card from "./Card.vue";

// Références pour les données de la game
const game = ref<Game | null>(null);
const status = ref<string | null>(null);
const gameId = ref<string | null>(null);

const fetchGame = async () => {
	try {
		// Déstructuration des valeurs retournées par la fonction
		const { status: fetchedStatus, game: fetchedGame, gameId: fetchedGameId } = await getInitGameTemplate();
		status.value = fetchedStatus;
		game.value = fetchedGame;
		gameId.value = fetchedGameId;

		console.log("Game loaded:", JSON.stringify(game.value, null, 2));
		console.log("Status:", status.value);
		console.log("Game ID:", gameId.value);
	} catch (error) {
		console.error("Error loading game:", error);
	}
};
</script>

<template>
	<div class="flex flex-col justify-center items-center bg-gray-900">
		<!-- Bouton pour lancer le fetch -->
		<button
			@click="fetchGame"
			class="bg-blue-500 text-white px-4 py-2 rounded shadow hover:bg-blue-600 mb-4"
		>
			Charger la game
		</button>

		<!-- Affichage du status et du gameId -->
		<div v-if="status" class="text-white mb-4">
			<p><strong>Status:</strong> {{ status }}</p>
			<p><strong>Game ID:</strong> {{ gameId }}</p>
		</div>

		<!-- GameBoard -->
		<div
			id="GameBoard"
			class="flex flex-col items-center gap-8 bg-gray-800 text-white p-4 rounded-md"
			style="transform-origin: top left"
			v-if="game"
		>
			<!-- Enemy Board -->
			<div class="w-full flex flex-col items-center">
				<div class="flex w-full justify-start space-x-10 pb-4">
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ game.enemy.name }}</h2>
					<p class="text-sm text-gray-300 mt-2">Life: {{ game.enemy.life }} | Pillz: {{ game.enemy.pillz }}</p>
				</div>
				<div class="flex flex-wrap justify-center gap-4">
					<Card v-for="(card, index) in game.enemy.cards" :key="'enemy-' + index" :card="card" />
				</div>
			</div>

			<!-- Ally Board -->
			<div class="w-full flex flex-col items-center">
				<div class="flex flex-wrap justify-center gap-4">
					<Card v-for="(card, index) in game.ally.cards" :key="'ally-' + index" :card="card" />
				</div>
				<div class="flex w-full justify-end space-x-10 pt-4">
					<p class="text-sm text-gray-300 mt-2">Life: {{ game.ally.life }} | Pillz: {{ game.ally.pillz }}</p>
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ game.ally.name }}</h2>
				</div>
			</div>
		</div>
	</div>
</template>
