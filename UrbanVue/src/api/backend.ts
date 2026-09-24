/** Adresse du backend, et URL des images de cartes : elles passent par son cache local (voir
 * `/card_image/` côté FastAPI), si bien que le front ne parle jamais au CDN d'Urban Rivals. */
export const API_BASE_URL = "http://127.0.0.1:8000";

/** Traduit l'URL CDN renvoyée par le backend en URL servie par son cache. Chaîne vide si la carte n'a pas d'image. */
export function cardImageUrl(cdnUrl: string): string {
	if (!cdnUrl) return "";
	const fileName = cdnUrl.split("/").pop();
	return fileName ? `${API_BASE_URL}/card_image/${fileName}` : "";
}
