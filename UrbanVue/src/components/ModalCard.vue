<script setup lang="ts">
import { ref } from "vue";
import CardDisplay from "./CardDisplay.vue";

const props = defineProps({
	isVisible: { type: Boolean, required: true },
	card: { type: Object, required: true },
	maxPillz: { type: Number, required: true },
});

const isFury = ref(false);
const currentPillz = ref(1);

const emit = defineEmits(["close", "combat"]);

const closeModal = () => emit("close");

const increasePillz = () => {
	if (isFury.value) {
		if (currentPillz.value + 3 < props.maxPillz) {
			currentPillz.value++;
		}
	} else {
		if (currentPillz.value < props.maxPillz) {
			currentPillz.value++;
		}
	}
};

const decreasePillz = () => {
	if (currentPillz.value > 1) {
		currentPillz.value --;
	}
};

const confirmCombat = () => {
	emit("combat", currentPillz.value, isFury.value);
	closeModal();
};
</script>

<template>
	<div v-if="isVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click="closeModal">
		<div class="flex bg-gray-900 p-4 rounded-md" @click.stop>
			<CardDisplay :card="card" />

			<div class="flex flex-col items-center justify-center pl-4 space-y-4 w-[350px]">
				<div class="flex items-center space-x-4">
					<button :disabled="currentPillz <= 1" @click="decreasePillz()" class="bg-gray-700 p-2 rounded text-white">-</button>
					<span class="text-white urbanFont">{{ currentPillz }}</span>
					<button @click="increasePillz" class="bg-gray-700 p-2 rounded text-white">+</button>
					<div class="cardPH urbanFont text-white">attaque: {{ currentPillz * card.power }}</div>
				</div>

				<div>
					<button
						:disabled="currentPillz + 3 > props.maxPillz"
						@click="isFury.valueOf = !isFury.valueOf"
						:class="`p-2 rounded text-white ${isFury.valueOf() ? 'bg-green-500 hover:bg-green-600' : 'bg-red-700 hover:bg-red-800'}`"
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

<style scoped>
button:disabled {
	cursor: not-allowed;
	opacity: 0.5;
	background-color: #4a5568;
}

.cardPH {
	font-size: 24px;
	text-align: center;
}

.urbanFont {
	font-family: "Urban Rivals", Arial, Sans-serif, Serif;
	font-weight: bolder;
	font-style: normal;
	font-variant: normal;
	text-shadow:
		-1px -1px 0 #00383f,
		1px -1px 0 #00383f,
		-1px 1px 0 #00383f,
		1px 1px 0 #00383f,
		2px 2px 1px #000;
}
</style>
