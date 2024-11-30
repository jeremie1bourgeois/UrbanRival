<script setup lang="ts">
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
});

const emit = defineEmits(["close"]);

const closeModal = () => {
	emit("close");
};
</script>

<template>
	<div v-if="isVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click="closeModal">
		<div class="bg-gray-900 p-4 rounded-md" @click.stop>
			<CardDisplay :card="card" />
		</div>
	</div>
</template>