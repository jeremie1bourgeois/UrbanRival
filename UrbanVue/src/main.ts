import { createApp } from "vue";
import App from "./App.vue";
import "./main.css";

// Import Font Awesome
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFireFlameCurved, faHeart } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

// Ajouter les icônes à la bibliothèque
library.add(faFireFlameCurved, faHeart);

// Créer l'application Vue
const app = createApp(App);

// Enregistrer le composant FontAwesomeIcon globalement
app.component("font-awesome-icon", FontAwesomeIcon);

// Monter l'application
app.mount("#app");
