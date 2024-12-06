<script setup lang="ts">
import { ref, onMounted } from "vue";
import CardDisplay from "./CardDisplay.vue";
import ModalCard from "./ModalCard.vue";

const props = defineProps({
	card: {
		type: Object,
		required: true,
		default: () => ({
			name: "",
			faction: "",
			stars: 0,
			power: 0,
			damage: 0,
			ability: "",
			bonus: "",
		}),
	},
	maxPillz: {
		type: Number,
		required: true,
	}, // Nombre maximal de pillz disponibles
});

onMounted(() => {
	console.log("Card loaded:", props.card);
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
	<ModalCard
		:isVisible="isModalVisible"
		:card="card"
		:maxPillz="maxPillz"
		@close="isModalVisible = false"
		@attack="handleAttack"
	/>
</template>
