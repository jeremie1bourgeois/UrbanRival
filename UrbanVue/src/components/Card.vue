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
const cardClasses = computed(() => "cursor-pointer");
</script>
<template>
	<div>
		<CardDisplay
			:class="cardClasses"
			:card="props.card"
			:isFight="props.card.played"
			@click="openModal"
		/>
		<div v-if="isModalVisible">
			<ModalCard
				:isVisible="isModalVisible"
				:card="props.card"
				@close="isModalVisible = false"
				:maxPillz="props.pillz"
				@combat="confirmCombat"
				:turn="props.turn"
			/>
		</div>
	</div>
</template>
