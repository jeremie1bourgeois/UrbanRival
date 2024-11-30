<script setup lang="ts">
import { computed } from "vue";
import ModalCard from "./ModalCard.vue";
import { ref } from "vue";
import CardDisplay from "./CardDisplay.vue";

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