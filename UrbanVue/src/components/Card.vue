<script setup lang="ts">
import ModalCard from "./ModalCard.vue";
import { ref } from "vue";
import CardDisplay from "./CardDisplay.vue";
import { Card } from "../models/game.interface";

const props = defineProps({
	card: {
		type: Object as () => Card,
		required: true,
	},
	pillz: {
		type: Number,
		required: true,
	},
});

const isModalVisible = ref(false);

const openModal = () => {
	isModalVisible.value = true;
};

const handleAttack = (data: { card: any; pillz: number }) => {
	console.log("Attacking with card:", data.card, "using pillz:", data.pillz);
	isModalVisible.value = false; // Fermer la modal après l'attaque
};
</script>

<template>
	<div class="cursor-pointer" @click="openModal">
		<CardDisplay :card="card" />
	</div>
	<ModalCard :isVisible="isModalVisible" :card="card" @close="isModalVisible = false" :maxPillz="props.pillz" />
</template>
