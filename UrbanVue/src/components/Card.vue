<script setup lang="ts">
import ModalCard from "./ModalCard.vue";
import { ref, computed } from "vue";
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

let isModalVisible = ref(false);

const openModal = () => {
	isModalVisible.value = true;
};

const emit = defineEmits(["combat"]);

const confirmCombat = (pillz: number, isFury: boolean) => {
	emit("combat", pillz, isFury);
};

// Calculer les classes dynamiques sous forme de chaîne
const cardClasses = computed(() =>
	[
		props.card.played ? "opacity-60" : "",
		props.turn ? "cursor-pointer" : "cursor-not-allowed",
	].join(" ")
);
</script>

<template>
	<div>
		<CardDisplay
			:class="cardClasses"
			:card="props.card"
			:isFight="props.card.played"
			@click="turn && openModal()"
		/>
		<div v-if="turn && isModalVisible">
			<ModalCard
				:isVisible="isModalVisible"
				:card="card"
				@close="isModalVisible = false"
				:maxPillz="props.pillz"
				@combat="confirmCombat"
			/>
		</div>
	</div>
</template>
