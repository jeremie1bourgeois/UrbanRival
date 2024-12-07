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
	turn: {
		type: Boolean,
		required: true,
	},
});

const isModalVisible = ref(false);

const openModal = () => {
	isModalVisible.value = true;
};

const emit = defineEmits(["combat"]);

const confirmCombat = (pillz: number, isFury: boolean) => {
	emit("combat", pillz, isFury);
};
</script>

<template>
	<div class="cursor-pointer" @click="openModal">
		<CardDisplay :card="card" />
	</div>
	<div v-if="turn">
		<ModalCard
			:isVisible="isModalVisible"
			:card="card"
			@close="isModalVisible = false"
			:maxPillz="props.pillz"
			@combat="confirmCombat"
		/>
	</div>
</template>
