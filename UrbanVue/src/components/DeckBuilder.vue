<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { errorMessage, getCatalogue, getInitGameTemplate, initGame, type StartedGame } from "../api/game";
import { cardImageUrl } from "../api/backend";
import {
	DECK_SIZE,
	MODES,
	clanBonusStatus,
	emptySlots,
	filterCatalogue,
	isDeckComplete,
	randomDeck,
	situationError,
	toDeck,
	type DeckSlots,
} from "../logic/deck";
import { loadSavedDecks, saveDecks } from "../logic/storage";
import type { CatalogueCard, CatalogueLevel, FirstPlayer, Situation } from "../models/game.interface";
import type { Side } from "../logic/round";

const emit = defineEmits<{ start: [StartedGame] }>();

const catalogue = ref<CatalogueCard[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const query = ref("");
const clanFilter = ref("");
const side = ref<Side>("ally");
const slots = ref<Record<Side, DeckSlots>>(loadSavedDecks() ?? { ally: emptySlots(), enemy: emptySlots() });
// Situation de départ : ce qui distingue un mode de jeu (vies et pillz de chaque joueur, premier joueur du round 1).
const situation = ref<Situation>({ life: [...MODES[0].life], pillz: [...MODES[0].pillz], first: MODES[0].first });
const FIRST_LABELS: Record<FirstPlayer, string> = { random: "Tiré au sort", player1: "Allié (toi)", player2: "Ennemi" };

const byName = computed(() => new Map(catalogue.value.map((card) => [card.name, card])));
const clans = computed(() => [...new Set(catalogue.value.map((card) => card.faction))].sort());
const results = computed(() => {
	const pool = clanFilter.value ? catalogue.value.filter((card) => card.faction === clanFilter.value) : catalogue.value;
	return query.value.trim() ? filterCatalogue(pool, query.value) : clanFilter.value ? pool.slice(0, 40) : [];
});
const status = computed(() => ({ ally: clanBonusStatus(slots.value.ally, byName.value), enemy: clanBonusStatus(slots.value.enemy, byName.value) }));
const situationProblem = computed(() => situationError(situation.value));
const ready = computed(() => isDeckComplete(slots.value.ally) && isDeckComplete(slots.value.enemy) && !situationProblem.value);
/** Le mode dont les valeurs sont celles saisies, ou « Personnalisé » (Survivor, Coliseum…). */
const mode = computed({
	get: () =>
		MODES.find(
			(m) =>
				m.life.every((v, i) => v === situation.value.life[i]) &&
				m.pillz.every((v, i) => v === situation.value.pillz[i]) &&
				m.first === situation.value.first,
		)?.label ?? "",
	set: (label: string) => {
		const preset = MODES.find((m) => m.label === label);
		if (preset) situation.value = { life: [...preset.life], pillz: [...preset.pillz], first: preset.first };
	},
});

watch(slots, (value) => saveDecks(value), { deep: true });

async function loadCatalogue() {
	loading.value = true;
	error.value = null;
	try {
		catalogue.value = await getCatalogue();
	} catch (err) {
		error.value = errorMessage(err);
	} finally {
		loading.value = false;
	}
}

onMounted(loadCatalogue);

function add(card: CatalogueCard, level: CatalogueLevel) {
	const target = slots.value[side.value];
	const free = target.findIndex((slot) => slot === null);
	if (free === -1) return;
	target[free] = { card_name: card.name, nb_stars: level.stars };
	if (isDeckComplete(target) && side.value === "ally" && !isDeckComplete(slots.value.enemy)) side.value = "enemy";
}

function remove(which: Side, index: number) {
	slots.value[which][index] = null;
}

function fillRandom(which: Side) {
	slots.value[which] = randomDeck(catalogue.value);
}

function clear(which: Side) {
	slots.value[which] = emptySlots();
}

async function start() {
	if (!isDeckComplete(slots.value.ally) || !isDeckComplete(slots.value.enemy)) return;
	error.value = null;
	try {
		emit("start", await initGame(toDeck(slots.value.ally, slots.value.enemy, situation.value)));
	} catch (err) {
		error.value = errorMessage(err);
	}
}

async function startTemplate() {
	error.value = null;
	try {
		emit("start", await getInitGameTemplate());
	} catch (err) {
		error.value = errorMessage(err);
	}
}
</script>

<template>
	<div class="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
		<header class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl font-bold text-yellow-400">Composer les decks</h1>
			<div class="flex flex-wrap items-center gap-3 text-sm">
				<span class="text-gray-400">Deux joueurs sur le même écran</span>
				<button class="rounded bg-gray-700 px-3 py-2 hover:bg-gray-600" @click="startTemplate">Partie d'exemple</button>
			</div>
		</header>

		<section class="flex flex-wrap items-end gap-4 rounded-xl border border-gray-700 bg-gray-800/50 p-4 text-sm">
			<label class="flex flex-col gap-1">
				Mode
				<select v-model="mode" class="rounded bg-gray-800 px-2 py-1">
					<option v-for="preset in MODES" :key="preset.label" :value="preset.label">{{ preset.label }}</option>
					<option value="">Personnalisé (Survivor, Coliseum…)</option>
				</select>
			</label>
			<fieldset v-for="(label, key) in { life: 'Vies', pillz: 'Pillz' }" :key="key" class="flex items-end gap-2">
				<legend class="mb-1">{{ label }} de départ</legend>
				<label v-for="(who, index) in ['allié', 'ennemi']" :key="who" class="flex flex-col gap-1 text-xs text-gray-400">
					{{ who }}
					<input
						v-model.number="situation[key][index]"
						type="number"
						:min="key === 'life' ? 1 : 0"
						max="99"
						class="w-16 rounded bg-gray-800 px-2 py-1 text-sm text-white"
					/>
				</label>
			</fieldset>
			<label class="flex flex-col gap-1">
				Premier joueur
				<select v-model="situation.first" class="rounded bg-gray-800 px-2 py-1">
					<option v-for="(label, key) in FIRST_LABELS" :key="key" :value="key">{{ label }}</option>
				</select>
			</label>
			<p v-if="situationProblem" class="text-red-300">{{ situationProblem }}</p>
		</section>

		<p v-if="error" class="flex items-center justify-between gap-3 rounded border border-red-500 bg-red-900/40 p-3 text-red-200">
			<span>{{ error }}</span>
			<button v-if="!catalogue.length" class="rounded bg-red-700 px-3 py-1 text-sm text-white hover:bg-red-600" @click="loadCatalogue">
				Réessayer
			</button>
		</p>

		<section class="grid gap-6 md:grid-cols-2">
			<div
				v-for="which in ['ally', 'enemy'] as Side[]"
				:key="which"
				class="rounded-xl border p-4"
				:class="side === which ? 'border-yellow-400 bg-gray-800' : 'border-gray-700 bg-gray-800/50'"
			>
				<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
					<h2 class="font-bold">{{ which === "ally" ? "Allié (toi)" : "Ennemi" }}</h2>
					<div class="flex gap-1 text-xs">
						<button class="rounded px-2 py-1" :class="side === which ? 'bg-yellow-500 text-black' : 'bg-gray-700'" @click="side = which">
							{{ side === which ? "sélection en cours" : "remplir" }}
						</button>
						<button class="rounded bg-gray-700 px-2 py-1 hover:bg-gray-600" :disabled="!catalogue.length" @click="fillRandom(which)">
							aléatoire
						</button>
						<button class="rounded bg-gray-700 px-2 py-1 hover:bg-gray-600" @click="clear(which)">vider</button>
					</div>
				</div>
				<ol class="space-y-1">
					<li
						v-for="(slot, index) in slots[which]"
						:key="index"
						class="flex items-center justify-between rounded bg-gray-900 px-3 py-2 text-sm"
					>
						<span v-if="slot">
							{{ slot.card_name }} <span class="text-yellow-400">{{ "★".repeat(slot.nb_stars) }}</span>
							<span class="text-xs text-gray-400">{{ byName.get(slot.card_name)?.faction ?? "" }}</span>
						</span>
						<span v-else class="text-gray-500">emplacement {{ index + 1 }} / {{ DECK_SIZE }}</span>
						<button v-if="slot" class="text-red-400 hover:text-red-300" @click="remove(which, index)">retirer</button>
					</li>
				</ol>
				<ul v-if="status[which].length" class="mt-3 flex flex-wrap gap-2 text-xs">
					<li
						v-for="clan in status[which]"
						:key="clan.clan"
						class="rounded px-2 py-0.5"
						:class="clan.active ? 'bg-green-800 text-green-100' : 'bg-gray-700 text-gray-300'"
						:title="clan.active ? 'Bonus de clan actif' : 'Bonus de clan inactif (il faut au moins deux cartes du clan)'"
					>
						{{ clan.clan }} × {{ clan.count }} · bonus {{ clan.active ? "actif" : "inactif" }}
					</li>
				</ul>
			</div>
		</section>

		<section class="space-y-3">
			<div class="flex flex-wrap gap-3">
				<input
					v-model="query"
					type="search"
					:placeholder="loading ? 'Chargement du catalogue…' : `Rechercher une carte ou un clan parmi ${catalogue.length} cartes`"
					:disabled="loading"
					class="min-w-[16rem] flex-1 rounded bg-gray-800 px-4 py-3 text-white outline-none ring-yellow-400 focus:ring-2"
				/>
				<select v-model="clanFilter" class="rounded bg-gray-800 px-3 py-3 text-white" :disabled="loading">
					<option value="">Tous les clans</option>
					<option v-for="clan in clans" :key="clan" :value="clan">{{ clan }}</option>
				</select>
			</div>
			<ul v-if="results.length" class="divide-y divide-gray-700 rounded-xl bg-gray-800">
				<li v-for="card in results" :key="card.name" class="flex flex-wrap items-center gap-3 px-4 py-2">
					<img v-if="card.clan_image" :src="cardImageUrl(card.clan_image)" :alt="card.faction" class="h-6 w-6" loading="lazy" />
					<div class="w-48">
						<div class="font-semibold">{{ card.name }}</div>
						<div class="text-xs text-gray-400">
							{{ card.faction }} · {{ card.bonus }}
							<span v-if="!card.bonus_supported" class="rounded bg-orange-700 px-1 text-orange-100">non géré</span>
						</div>
					</div>
					<button
						v-for="level in card.levels"
						:key="level.stars"
						class="rounded border border-gray-600 px-2 py-1 text-left text-xs hover:border-yellow-400 hover:bg-gray-700"
						:title="level.ability"
						@click="add(card, level)"
					>
						<img
							v-if="level.image"
							:src="cardImageUrl(level.image)"
							:alt="`${card.name} ${level.stars}★`"
							class="mx-auto h-16 rounded"
							loading="lazy"
						/>
						<div class="text-yellow-400">{{ "★".repeat(level.stars) }}</div>
						<div>P{{ level.power }} D{{ level.damage }}</div>
						<div class="max-w-[10rem] truncate text-gray-300">{{ level.ability }}</div>
						<div v-if="!level.ability_supported" class="rounded bg-orange-700 px-1 text-center text-orange-100">non géré</div>
					</button>
				</li>
			</ul>
			<p v-else-if="(query.trim() || clanFilter) && !loading" class="text-gray-400">Aucune carte ne correspond.</p>
		</section>

		<footer class="flex justify-end">
			<button
				class="rounded bg-yellow-500 px-6 py-3 font-bold text-black disabled:cursor-not-allowed disabled:opacity-40"
				:disabled="!ready"
				@click="start"
			>
				Lancer la partie
			</button>
		</footer>
	</div>
</template>
