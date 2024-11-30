<script setup lang="ts">
import { ref, onMounted } from "vue";
import Card from "@/components/Card.vue";

// Données du jeu
const data = ref({
	game: {
		nb_turn: 0,
		turn: "",
		ally: {
			name: "",
			life: 0,
			pillz: 0,
			cards: [],
		},
		enemy: {
			name: "",
			life: 0,
			pillz: 0,
			cards: [],
		},
	},
});

// Charger les données JSON
onMounted(async () => {
	const response = await fetch("../game.json");
	data.value = await response.json();
});

window.addEventListener("load", scaleDiv);
window.addEventListener("resize", scaleDiv);

function scaleDiv() {
	const div = document.querySelector("#GameBoard");
	if (!div) return;
	const scaleX = window.innerWidth / (div as HTMLElement).offsetWidth;
	const scaleY = window.innerHeight / (div as HTMLElement).offsetHeight;
	const scale = Math.min(scaleX, scaleY);
	console.log("scale", scale);
	(div as HTMLElement).style.transform = `scale(${scale})`;
}

scaleDiv();
</script>

<template>
	<div class="flex justify-center items-center bg-gray-900">
		<div
			id="GameBoard"
			class="flex flex-col items-center gap-8 bg-gray-800 text-white p-4 rounded-md"
			style="transform: scale(1); transform-origin: top left"
		>
			<div class="w-full flex flex-col items-center">
				<div class="flex w-full justify-start space-x-10 pb-4">
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ data.game.enemy.name }}</h2>
					<p class="text-sm text-gray-300 mt-2">Life: {{ data.game.enemy.life }} | Pillz: {{ data.game.enemy.pillz }}</p>
				</div>
				<div class="flex flex-wrap justify-center gap-4">
					<Card v-for="(card, index) in data.game.enemy.cards" :key="'enemy-' + index" :card="card" />
				</div>
			</div>
			<div class="w-full flex flex-col items-center">
				<div class="flex flex-wrap justify-center gap-4">
					<Card v-for="(card, index) in data.game.ally.cards" :key="'ally-' + index" :card="card" />
				</div>
				<div class="flex w-full justify-end space-x-10 pt-4">
					<p class="text-sm text-gray-300 mt-2">Life: {{ data.game.ally.life }} | Pillz: {{ data.game.ally.pillz }}</p>
					<h2 class="text-xl font-bold text-yellow-400 mb-2">{{ data.game.ally.name }}</h2>
				</div>
			</div>
		</div>
	</div>
</template>
