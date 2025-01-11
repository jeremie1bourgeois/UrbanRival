<script setup lang="ts">
import { computed } from "vue";
import { Card } from "../models/game.interface";

const props = defineProps({
	card: {
		type: Object as () => Card,
		required: true,
	},
	isFight: {
		type: Boolean,
		default: false,
		required: false,
	},
});

const imageSrc = computed(() => {
	if (!props.card.name) return "src/assets/default-card.jpg";
	return "src/assets/imageCard/" + `${props.card.name.replace(/\s+/g, "_")}_${props.card.stars}.jpg`;
});

const clanSrc = computed(() => {
	if (!props.card.faction) return "src/assets/default-clan.jpg";
	return "src/assets/Clan/" + props.card.faction.replace(/\s+/g, "").toUpperCase() + ".jpg";
});

const pillzUsed = computed(() => {
	return props.card.played ? `${props.card.pillz_fight}` : "";
});

const attack = computed(() => {
	return props.card.played ? `${props.card.attack}` : "";
});

const trophyClass = computed(() => {
	return props.card.win ? "trophyIcon-clear" : "trophyIcon-gray";
});

const damageClass = computed(() => {
	if (!props.isFight) return "";
	return props.card.damage_fight > props.card.damage ? "text-violet-500" : "text-orange-500";
});

const powerClass = computed(() => {
	if (!props.isFight) return "";
	return props.card.power_fight > props.card.power ? "text-violet-500" : "text-orange-500";
});
</script>

<template>
	<div
		class="bg-gray-800 text-white border border-gray-700 rounded-md shadow-md w-[166px] h-[237px] text-center cardFrame urbanFont"
		:style="{ backgroundImage: `url(${imageSrc})`, backgroundSize: 'cover', backgroundPosition: 'center' }"
		:class="[card.played ? 'card-played' : '']"
	>
		<div class="cardHeader flex items-center">
			<img alt="Clan Image" :src="clanSrc" class="cardClanPict" />
			<span class="cardName urbanFont">{{ card.name }}</span>
		</div>

		<div v-if="pillzUsed" class="pillzBanner pillzUsed" :class="[card.played ? 'pillz-active' : '']">
				<img :class="trophyClass" src="../assets/icons8-trophy-50.png" alt="Trophy Icon" style="opacity: 1; margin-right: 10px;" />
				{{ pillzUsed }}
				<img src="../assets/icons8-pill-50.png" alt="Pillz Icon" class="pillzIcon" style="background-color: white; margin-right: 10px;" />
				{{ attack }}
				<img src="../assets/epee.png" alt="Sword Icon" class="pillzIcon" style="background-color: white; margin-right: 10px;" />
		</div>

		<div class="cardBottom">
			<div class="cardStars">
				<div v-for="i in card.stars" :key="'star-on-' + i" class="cardStarOn"></div>
				<div v-for="i in card.starOff - card.stars" :key="'star-off-' + i" class="cardStarOff"></div>
			</div>
			<div class="cardDescription">
				<div class="flex h-[30px] items-center">
					<img src="../assets/Power.png" alt="Power Image" class="w-[22px] h-[22px]" />
						<div :class="['cardPH urbanFont', powerClass]">{{ isFight ? card.power_fight : card.power }}</div>
					<img src="../assets/Ability.png" alt="Ability Image" class="w-[22px] h-[22px] ml-1" />
					<div class="vcenterContent">{{ card.ability_description || "N/A" }}</div>
				</div>

				<div class="flex h-[30px] items-center">
					<img src="../assets/Damage.png" alt="Damage Image" class="w-[22px] h-[22px]" />
						<div :class="['cardPH urbanFont', damageClass]">{{ isFight ? card.damage_fight : card.damage }}</div>
					<img src="../assets/Bonus.png" alt="Bonus Image" class="w-[22px] h-[22px] ml-1" />
					<div class="vcenterContent">{{ card.bonus_description || "N/A" }}</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
@font-face {
	font-family: "Urban Rivals";
	src: url("@/assets/urbanrivalsfont-webfont.woff") format("woff");
	font-weight: normal;
	font-style: normal;
}

.cardFrame {
	position: relative;
	text-align: left;
	font-family: Arial, Sans-serif;
	color: white;
	background-repeat: no-repeat;
	width: 166px;
	height: 237px;
	z-index: 10;
	overflow: hidden;
	border-radius: 8px;
	display: flex;
	flex-direction: column;
}

.cardHeader {
	display: flex;
	align-items: center;
	padding: 4px;
}

.cardName {
	font-size: 14px;
	text-align: left;
	text-shadow:
		-1px -1px 0 #00383f,
		1px -1px 0 #00383f,
		-1px 1px 0 #00383f,
		1px 1px 0 #00383f,
		2px 2px 1px #000;
	z-index: 28;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cardClanPict {
	width: 32px;
	height: 32px;
	margin-right: 8px;
}

.cardStars {
	height: 16px;
	width: 164px;
	padding-left: 6px;
	background: url(../assets/Bg-Gauge.png) no-repeat;
	margin-top: auto;
}

.cardStarOn,
.cardStarOff {
	display: inline-block;
	width: 25px;
	height: 25px;
	background-repeat: no-repeat;
	z-index: 4;
	margin-top: -8px;
}
.cardStarOn {
	background: url(../assets/Star-On.png) no-repeat;
}
.cardStarOff {
	background: url(../assets/Star-Off.png) no-repeat;
}

.cardDescription {
	height: 69px;
	width: 166px;
	background: url(../assets/Bg-Bottom.png) no-repeat;
}

.cardBottom {
	margin-top: auto;
}

.cardPH {
	font-size: 24px;
	width: 19px;
	text-align: center;
	text-shadow:
		-1px -1px 0 #00383f,
		1px -1px 0 #00383f,
		-1px 1px 0 #00383f,
		1px 1px 0 #00383f,
		2px 2px 1px #000;
}

.vcenterContent {
	font-size: 9px;
}

.card-played {
	opacity: 0.6; /* Réduit l'opacité de la carte */
}

.pillzBanner.pillz-active {
	opacity: 1; /* Maintient le bandeau de pillz à 100% */
	position: relative; /* Assurez-vous que la position reste correcte */
	z-index: 11; /* Permet de s'assurer que le contenu est visible au-dessus */
	top: 35%; /* Ajuste la position verticale pour être plus haut sur la carte */
}


.pillzBanner {
	position: absolute;
	top: 50%;
	left: 0;
	transform: translateY(-50%);
	width: 100%;
	background-color: rgba(0, 0, 0, 0.7);
	padding: 4px 0;
	text-align: center;
	border-radius: 4px;
	opacity: 1;
}

.pillzUsed {
	font-size: 14px;
	color: yellow;
	display: flex;
	justify-content: center;
	align-items: center;
}

.pillzIcon {
	width: 16px;
	height: 16px;
	margin-left: 4px;
}

.trophyIcon-clear {
	width: 20px; /* Increased size */
	height: 20px; /* Increased size */
	margin-right: 4px;
	filter: none;
	opacity: 1;
}

.trophyIcon-gray {
	width: 20px; /* Increased size */
	height: 20px; /* Increased size */
	margin-right: 4px;
	filter: grayscale(100%);
	opacity: 1;
}
</style>
