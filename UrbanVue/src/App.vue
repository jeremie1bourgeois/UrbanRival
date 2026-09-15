<script setup lang="ts">
import { ref } from "vue";
import DeckBuilder from "./components/DeckBuilder.vue";
import GameBoard from "./components/GameBoard.vue";
import type { StartedGame } from "./api/game";

const started = ref<StartedGame | null>(null);
</script>

<template>
	<div class="min-h-screen w-full bg-gray-900 text-white">
		<DeckBuilder v-if="started === null" @start="(game) => (started = game)" />
		<GameBoard v-else :started="started" @new-game="started = null" />
	</div>
</template>
