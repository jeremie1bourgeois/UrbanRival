<script setup lang="ts">
import { ref } from "vue";
import CardDisplay from "./CardDisplay.vue";

defineProps({
	isVisible: {
		type: Boolean,
		required: true,
	},
	card: {
		type: Object,
		required: true,
	},	
	maxPillz: {
		type: Number,
		required: true,
	},
});

const emit = defineEmits(["close", "attack"]);

const closeModal = () => {
	emit("close");
};

const selectedPillz = ref(0);

const confirmAttack = () => {
	emit("attack", { card: card, pillz: selectedPillz.value });
	closeModal();
};
</script>

<template>
	<div
		v-if="isVisible"
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		@click="closeModal"
	>
		<div class="bg-gray-900 p-6 rounded-md w-[400px]" @click.stop>
			<!-- Affichage de la carte -->
			<CardDisplay :card="card" />

			<!-- Sélecteur de pillz -->
			<div class="mt-4">
				<p class="text-white text-center mb-2">Sélectionnez le nombre de pillz :</p>
				<input
					type="range"
					class="w-full"
					min="0"
					:max="maxPillz"
					v-model="selectedPillz"
				/>
				<p class="text-white text-center mt-2">Pillz sélectionnés : {{ selectedPillz }}</p>
			</div>

			<!-- Bouton de validation -->
			<div class="flex justify-center mt-6">
				<button
					class="bg-green-500 text-white px-4 py-2 rounded shadow hover:bg-green-600"
					@click="confirmAttack"
				>
					Confirmer l'attaque
				</button>
			</div>

			<!-- Bouton de fermeture -->
			<div class="flex justify-center mt-4">
				<button
					class="bg-red-500 text-white px-4 py-2 rounded shadow hover:bg-red-600"
					@click="closeModal"
				>
					Annuler
				</button>
			</div>
		</div>
	</div>
</template>
