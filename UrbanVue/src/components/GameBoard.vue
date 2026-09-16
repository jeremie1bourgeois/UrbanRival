<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { OPPONENT_LABELS, aiPick, errorMessage, processGameRound, savePlayForTest, type StartedGame } from "../api/game";
import { roundSummaries } from "../logic/history";
import { RoundPicker, type Pick, type Side } from "../logic/round";
import type { Game, GameState, Player } from "../models/game.interface";
import Card from "./Card.vue";

const props = defineProps<{ started: StartedGame }>();
const emit = defineEmits<{ newGame: [] }>();

const game = ref<Game>(props.started.game);
const states = ref<Game[]>([props.started.game]);
const gameId = props.started.gameId;
const opponent = props.started.opponent;
const state = ref<GameState>("Game Not Finished");
const error = ref<string | null>(null);
const saved = ref(false);
const thinking = ref(false);
let picker = new RoundPicker(game.value);
const current = ref<Side | null>(picker.current);

const finished = computed(() => state.value !== "Game Not Finished");
const banner = computed(
	() => ({ "Ally Wins": "Victoire de l'allié !", "Enemy Wins": "Victoire de l'ennemi !", Draw: "Égalité.", "Game Not Finished": "" })[state.value],
);
const history = computed(() => roundSummaries(states.value));
const enemyIsAi = opponent !== "human";

const effectLabel = (kind: string, value: number, borne: number) =>
	({
		poison: `Poison ${value} (min ${borne})`,
		toxine: `Toxin ${value} (min ${borne})`,
		heal: `Heal ${value} (max ${borne})`,
		regen: `Regen ${value} (max ${borne})`,
		dope: `Dope ${value} (max ${borne})`,
		repair: `Repair ${value} (max ${borne})`,
	})[kind] ?? kind;

function effects(player: Player) {
	return player.effect_list.map((effect) => effectLabel(effect.kind, effect.value, effect.borne));
}

async function submitIfComplete(pick: Pick) {
	const roundData = picker.pick(pick);
	current.value = picker.current;
	if (roundData === null) return;
	error.value = null;
	try {
		const result = await processGameRound(gameId, roundData);
		game.value = result.game;
		states.value = [...states.value, result.game];
		state.value = result.state;
		saved.value = false;
	} catch (err) {
		error.value = errorMessage(err);
	}
	picker = new RoundPicker(game.value);
	current.value = finished.value ? null : picker.current;
}

/** L'ordinateur joue tant que c'est à lui (il peut jouer en premier ou en second). */
async function letAiPlay() {
	while (!finished.value && opponent !== "human" && current.value === "enemy") {
		thinking.value = true;
		try {
			const pick = await aiPick(gameId, opponent);
			await submitIfComplete({ index: pick.card_index, pillz: pick.pillz, fury: pick.fury });
		} catch (err) {
			error.value = errorMessage(err);
			break;
		} finally {
			thinking.value = false;
		}
	}
}

async function handleCombat(pillz: number, fury: boolean, index: number) {
	await submitIfComplete({ index, pillz, fury });
	await letAiPlay();
}

onMounted(letAiPlay);

async function save() {
	try {
		await savePlayForTest(gameId);
		saved.value = true;
	} catch (err) {
		error.value = errorMessage(err);
	}
}
</script>

<template>
	<div class="flex min-h-screen flex-col items-center gap-4 p-2 sm:p-4">
		<header class="flex w-full max-w-5xl flex-wrap items-center justify-between gap-2 text-sm text-gray-300">
			<span>Partie #{{ gameId }} · round {{ Math.min(game.nb_turn, 4) }} / 4 · {{ OPPONENT_LABELS[opponent] }}</span>
			<span v-if="!finished">
				<template v-if="thinking">L'ordinateur réfléchit…</template>
				<template v-else
					>Au tour de :
					<strong class="text-yellow-400">{{ current === "ally" ? "toi" : enemyIsAi ? "l'ordinateur" : "l'ennemi" }}</strong></template
				>
			</span>
			<button class="rounded bg-gray-700 px-3 py-1 hover:bg-gray-600" @click="emit('newGame')">Nouvelle partie</button>
		</header>

		<p v-if="error" class="w-full max-w-5xl rounded border border-red-500 bg-red-900/40 p-3 text-red-200">{{ error }}</p>
		<p
			v-if="finished"
			class="w-full max-w-5xl rounded border border-yellow-400 bg-yellow-900/40 p-3 text-center text-xl font-bold text-yellow-200"
		>
			{{ banner }}
		</p>

		<div id="GameBoard" class="flex w-full max-w-5xl flex-col items-center gap-6 rounded-xl bg-gray-800">
			<section
				class="flex w-full flex-col items-center rounded-xl p-4"
				:class="{ 'bg-gradient-to-b from-blue-800 to-gray-800': current === 'enemy' }"
			>
				<div class="flex w-full flex-wrap items-center justify-start gap-4 pb-4">
					<h2 class="text-xl font-bold text-yellow-400">{{ game.enemy.name }}</h2>
					<p class="text-sm text-gray-300">
						{{ game.enemy.life }} <font-awesome-icon :icon="['fas', 'heart']" class="text-red-500" /> | Pillz : {{ game.enemy.pillz }}
					</p>
					<span v-for="label in effects(game.enemy)" :key="label" class="rounded bg-purple-800 px-2 py-0.5 text-xs">{{ label }}</span>
				</div>
				<div class="flex flex-wrap justify-center gap-3">
					<Card
						v-for="(card, index) in game.enemy.cards"
						:key="'enemy-' + index"
						:card="card"
						:pillz="game.enemy.pillz"
						:turn="!enemyIsAi && current === 'enemy'"
						@combat="(pillz, fury) => handleCombat(pillz, fury, index)"
					/>
				</div>
			</section>

			<div class="w-[95%] border-t border-gray-600"></div>

			<section
				class="flex w-full flex-col items-center rounded-xl p-4"
				:class="{ 'bg-gradient-to-b from-gray-800 to-blue-900': current === 'ally' }"
			>
				<div class="flex flex-wrap justify-center gap-3">
					<Card
						v-for="(card, index) in game.ally.cards"
						:key="'ally-' + index"
						:card="card"
						:pillz="game.ally.pillz"
						:turn="current === 'ally' && !thinking"
						@combat="(pillz, fury) => handleCombat(pillz, fury, index)"
					/>
				</div>
				<div class="flex w-full flex-wrap items-center justify-end gap-4 pt-4">
					<span v-for="label in effects(game.ally)" :key="label" class="rounded bg-purple-800 px-2 py-0.5 text-xs">{{ label }}</span>
					<p class="text-sm text-gray-300">
						{{ game.ally.life }} <font-awesome-icon :icon="['fas', 'heart']" class="text-red-500" /> | Pillz : {{ game.ally.pillz }}
					</p>
					<h2 class="text-xl font-bold text-yellow-400">{{ game.ally.name }}</h2>
				</div>
			</section>

			<section v-if="history.length" class="w-full px-4 pb-2">
				<h3 class="mb-2 text-sm font-bold text-gray-300">Historique</h3>
				<table class="w-full text-left text-xs text-gray-200">
					<thead class="text-gray-400">
						<tr>
							<th class="py-1 pr-2">Round</th>
							<th class="py-1 pr-2">Allié</th>
							<th class="py-1 pr-2">Ennemi</th>
							<th class="py-1">Vie après</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="round in history" :key="round.round" class="border-t border-gray-700">
							<td class="py-1 pr-2">{{ round.round }}</td>
							<td
								v-for="(played, who) in { ally: round.ally, enemy: round.enemy }"
								:key="who"
								class="py-1 pr-2"
								:class="played.win ? 'text-green-300' : 'text-gray-400'"
							>
								{{ played.name }} · {{ played.pillz }} pillz<template v-if="played.fury"> + fury</template> · P{{ played.power }} D{{
									played.damage
								}}
								· attaque {{ played.attack }}
								<span v-if="played.win">✓</span>
							</td>
							<td class="py-1">{{ round.lifeAfter.ally }} / {{ round.lifeAfter.enemy }}</td>
						</tr>
					</tbody>
				</table>
			</section>

			<button
				:disabled="saved || game.nb_turn <= 1"
				class="mb-4 rounded bg-green-600 px-4 py-2 text-white hover:bg-green-500 disabled:opacity-40"
				@click="save"
			>
				{{ saved ? "Round sauvegardé pour les tests" : "Sauvegarder le dernier round pour les tests" }}
			</button>
		</div>
	</div>
</template>
