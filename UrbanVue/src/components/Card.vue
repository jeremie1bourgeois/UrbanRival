<script setup lang="ts">
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
	pillz: {
		type: Number,
		required: true,
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
	<ModalCard :isVisible="isModalVisible" :card="card" @close="isModalVisible = false" :maxPillz="props.pillz" />
</template>