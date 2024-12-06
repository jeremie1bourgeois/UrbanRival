<script setup lang="ts">
import { onMounted, ref } from "vue";
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
});

onMounted(() => {
	console.log("Card loaded:", props.card);
});

const isModalVisible = ref(false);

const openModal = () => {
	isModalVisible.value = true;
};
</script>

<template>
	<div class="cursor-pointer" @click="openModal">
		<CardDisplay :card="card" />
	</div>
	<ModalCard :isVisible="isModalVisible" :card="card" @close="isModalVisible = false" />
</template>