<script setup lang="ts">
import { ref, computed } from "vue";
import CardDisplay from "./CardDisplay.vue";
import { Card } from "../models/game.interface";

const props = defineProps({
	isVisible: { type: Boolean, required: true },
	card: { type: Object as () => Card, required: true },
	maxPillz: { type: Number, required: true },
	turn: { type: Boolean, required: true },
});

const isFury = ref<boolean>(false);
const selectedPillz = ref<number>(1); // Start at 1 as the initial value

const emit = defineEmits(["close", "combat"]);

const closeModal = () => {
	emit("close");
};

const confirmCombat = () => {
	emit("combat", selectedPillz.value, isFury.value);
	closeModal();
};

const toggleFury = () => {
	isFury.value = !isFury.value;
};

const increasePillz = () => {
	if (selectedPillz.value < props.maxPillz + 1 && (!isFury.value || selectedPillz.value < props.maxPillz - 2)) {
		// Allow up to maxPillz + 1, but restrict last three when Fury is active
		selectedPillz.value++;
	}
};

const decreasePillz = () => {
	if (selectedPillz.value > 1) {
		// Allow minimum value to be 1
		selectedPillz.value--;
	}
};

const isLastThreePillz = (pillz: number) => {
	return isFury.value && pillz > props.maxPillz + 1 - 3;
};

// Generate a range of numbers for pillz buttons, starting from 2
const pillzArray = computed(() => Array.from({ length: props.maxPillz }, (_, i) => i + 2));
</script>

<template>
	<div v-if="isVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="closeModal">
		<div class="flex bg-gray-900 p-4 rounded-md">
			<CardDisplay :card="card" />

			<div v-if="turn && !card.played" class="flex flex-col items-center justify-center pl-4 space-y-4 w-[470px]">
				<div class="flex items-center space-x-2">
					<!-- Decrease Pillz Button -->
					<button @click="decreasePillz" :disabled="selectedPillz === 1" class="change-nb-pillz-button bg-red-600 hover:bg-red-700">
						-
					</button>

					<!-- Pillz Buttons -->
					<div class="flex flex-wrap justify-center space-x-1.5">
						<button
							v-for="pillz in pillzArray"
							:key="pillz"
							@click="selectedPillz = pillz"
							:disabled="isFury && isLastThreePillz(pillz)"
							:class="`pillz-button ${pillz <= selectedPillz || (isFury && isLastThreePillz(pillz)) ? 'selected-pillz' : 'unselected-pillz'}`"
						>
							{{ pillz }}
							<font-awesome-icon v-if="isLastThreePillz(pillz)" :icon="['fas', 'fire-flame-curved']" class="text-red-500" />
						</button>
					</div>

					<!-- Increase Pillz Button -->
					<button
						@click="increasePillz"
						:disabled="selectedPillz === props.maxPillz + 1"
						class="change-nb-pillz-button bg-green-600 hover:bg-green-700"
					>
						+
					</button>
				</div>

				<div class="text-2xl text-center urbanFont text-white">Attaque: {{ selectedPillz * card.power }}</div>

				<div>
					<button
						:disabled="selectedPillz + 3 > props.maxPillz + 1"
						@click="toggleFury"
						:class="`p-2 rounded text-white ${isFury ? 'bg-red-700 hover:bg-red-800' : 'bg-gray-500 hover:bg-gray-600'}`"
					>
						Fury
					</button>
				</div>

				<div class="w-full flex justify-center">
					<button
						@click="confirmCombat"
						class="bg-yellow-500 text-black px-4 py-2 w-1/2 rounded font-bold hover:bg-yellow-600 self-stretch"
					>
						Combattre
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style>
button {
	cursor: pointer;
	transition:
		background-color 0.3s,
		transform 0.2s,
		box-shadow 0.2s;
}

button:hover {
	transform: translateY(-2px);
	box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

button:active {
	transform: translateY(0);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.pillz-button {
	width: 1.5rem;
	height: 3rem;
	border-radius: 1.5rem;
	border: 2px solid;
	font-weight: bold;
	text-emphasis: true;
}

.change-nb-pillz-button {
	width: 2rem;
	height: 2rem;
	border-radius: 50%;
	border: 2px solid;
	font-weight: bold;
	text-emphasis: true;
}

.selected-pillz {
	background: linear-gradient(to right, #3b82f6, #2563eb);
	border-color: #1e3a8a;
	color: white;
}

.selected-pillz.fury {
	background: linear-gradient(to right, #3b82f6, #2563eb);
	border-color: #1e3a8a;
	color: white;
}

.unselected-pillz {
	background: linear-gradient(to right, #d1d5db, #9ca3af);
	border-color: #6b7280;
	color: #374151;
}

.unselected-pillz:hover {
	background: linear-gradient(to right, #9ca3af, #6b7280);
	border-color: #4b5563;
	color: black;
}
</style>
