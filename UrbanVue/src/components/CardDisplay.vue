<script setup lang="ts">
import { computed } from "vue";
import { Card } from "@/models/game"; // Assurez-vous d'importer la bonne interface ou classe

const props = defineProps({
	card: {
		type: Object as () => Card, // Utilisation du type Card
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

// Source de l'image de la carte
const imageSrc = computed(() => {
	if (!props.card.name) return "src/assets/default-card.jpg"; // Fallback image
	return "src/assets/imageCard/" + `${props.card.name.replace(/\s+/g, "_")}_${props.card.stars}.jpg`;
});

// Source de l'image du clan
const clanSrc = computed(() => {
	if (!props.card.faction) return "src/assets/default-clan.jpg"; // Fallback image
	return "src/assets/Clan/" + props.card.faction.replace(/\s+/g, "").toUpperCase() + ".jpg";
});
</script>

<template>
	<div
		class="bg-gray-800 text-white border border-gray-700 rounded-md shadow-md w-[166px] h-[237px] text-center cardFrame urbanFont"
		:style="{ backgroundImage: `url(${imageSrc})`, backgroundSize: 'cover', backgroundPosition: 'center' }"
	>
		<!-- En-tête de la carte -->
		<div class="cardHeader flex items-center">
			<img alt="Clan Image" :src="clanSrc" class="cardClanPict" />
			<span class="cardName urbanFont">{{ card.name }}</span>
		</div>

		<!-- Corps de la carte -->
		<div class="cardBottom">
			<div class="cardStars">
				<div v-for="i in card.stars" :key="'star-on-' + i" class="cardStarOn"></div>
				<div v-for="i in 5 - card.stars" :key="'star-off-' + i" class="cardStarOff"></div>
			</div>
			<div class="cardDescription">
				<!-- Statistiques principales -->
				<div class="flex h-[30px] items-center">
					<img src="../assets/Power.png" alt="Power Image" class="w-[22px] h-[22px]" />
					<div class="cardPH urbanFont">{{ card.power }}</div>
					<img src="../assets/Ability.png" alt="Ability Image" class="w-[22px] h-[22px] ml-1" />
					<div class="vcenterContent">{{ card.ability?.type || 'N/A' }}</div>
				</div>

				<div class="flex h-[30px] items-center">
					<img src="../assets/Damage.png" alt="Damage Image" class="w-[22px] h-[22px]" />
					<div class="cardPH urbanFont">{{ card.damage }}</div>
					<img src="../assets/Bonus.png" alt="Bonus Image" class="w-[22px] h-[22px] ml-1" />
					<div class="vcenterContent">{{ card.bonus?.type || 'N/A' }}</div>
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

.urbanFont {
	font-family: "Urban Rivals", Arial, Sans-serif, Serif;
	font-weight: bolder;
	font-style: normal;
	font-variant: normal;
	text-shadow:
		-1px -1px 0 #00383f,
		1px -1px 0 #00383f,
		-1px 1px 0 #00383f,
		1px 1px 0 #00383f,
		2px 2px 1px #000;
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
</style>
