"""
Extraction des cartes depuis les pages HTML d'iclintz.com (fonctions pures, sans réseau).
Le téléchargement est dans scripts/scrape_official_cards.py.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup, Tag

BASE_URL = "https://iclintz.com"
CLANS_INDEX_URL = f"{BASE_URL}/"   # le menu de navigation de toute page liste les clans
CLAN_URL = f"{BASE_URL}/characters/clan.php?ID={{clan_id}}"

# Bonus jour/nuit (GhosTown) : iclintz n'affiche que le texte de l'heure de la visite, jamais les deux.
# Textes relevés le 2026-09-15 (Gunslinger visité de nuit, les 58 autres GhosTown de jour).
NIGHT_BONUS_OF_DAY_BONUS = {"Day: Power And Damage + 1": "Night: -1 Opp Pow. And Damage, Min 1"}
DAY_BONUS_OF_NIGHT_BONUS = {night: day for day, night in NIGHT_BONUS_OF_DAY_BONUS.items()}


@dataclass
class ScrapedLevel:
    stars: int
    power: int
    damage: int
    ability: str
    image: str


@dataclass
class ScrapedCard:
    id: int
    name: str
    faction: str
    star_off: int
    bonus: str
    clan_image: str
    levels: List[ScrapedLevel]
    night_ability: str = ""   # texte « Night: … » du badge lune, un seul par carte (iclintz ne le donne pas par niveau)
    night_bonus: str = ""


def clan_ids(index_html: str) -> List[int]:
    """Identifiants de clan référencés par le menu de navigation d'une page du site, triés et dédoublonnés."""
    return sorted({int(clan_id) for clan_id in re.findall(r"clan\.php\?ID=(\d+)", index_html)})


def card_links(clan_html: str) -> List[str]:
    """Liens relatifs des cartes d'une page de clan, dans l'ordre, sans doublon."""
    soup = BeautifulSoup(clan_html, "html.parser")
    links = []
    for frame in soup.find_all("div", {"class": "cardFrame"}):
        anchor = frame.find("a")
        href = anchor.get("href") if anchor else None
        if href and href not in links:
            links.append(href)
    return links


def _capacity_text(container: Tag) -> str:
    """
    Texte d'une ability / d'un bonus. Les clans visés sont des images : on les rend en texte.
    « Versus : X » + <img alt="Freaks"> <img alt="Oculus"> -> « Versus Freaks, Oculus: X » ; idem pour « After : X ».
    Oculus : « X » + images des clans infiltrables -> « Infiltrated La Junta, Piranas: X » (l'ability n'agit que si
    l'Oculus a infiltré l'un de ces clans).
    """
    content = container.find("div", {"class": "vcenterContent"}) or container
    clans = [img.get("alt", "").strip() for img in content.find_all("img", {"class": "clan"}) if img.get("alt")]
    text = re.sub(r"\s+", " ", content.get_text(" ", strip=True)).strip()
    if not clans:
        return text
    lowered = text.lower()
    for prefix in ("versus", "after"):
        if lowered.startswith(prefix):
            rest = text.split(":", 1)[1].strip() if ":" in text else ""
            return f"{prefix.capitalize()} {', '.join(clans)}: {rest}"
    return f"Infiltrated {', '.join(clans)}: {text}"


def _int(text: str) -> int:
    match = re.search(r"-?\d+", text or "")
    return int(match.group()) if match else 0


def _night_ability(soup: BeautifulSoup) -> str:
    """Le pouvoir de nuit est affiché hors des cadres de carte, dans un badge à icône de lune."""
    moon = soup.find("i", {"class": "bi-moon-stars-fill"})
    return re.sub(r"\s+", " ", moon.parent.get_text(" ", strip=True)).strip() if moon else ""


def _day_and_night_bonus(bonus: str) -> Tuple[str, str]:
    """Le bonus affiché est celui du jour ou de la nuit selon l'heure de la visite : on complète l'autre."""
    if bonus in NIGHT_BONUS_OF_DAY_BONUS:
        return bonus, NIGHT_BONUS_OF_DAY_BONUS[bonus]
    if bonus in DAY_BONUS_OF_NIGHT_BONUS:
        return DAY_BONUS_OF_NIGHT_BONUS[bonus], bonus
    return bonus, ""


def parse_card_page(html: str, card_id: int) -> ScrapedCard:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title").text.split("|", 1)[-1].strip()          # "Aamir - All Stars"
    name, _, faction = title.rpartition(" - ")                           # le nom peut contenir des tirets

    levels = []
    bonus, clan_image, star_off = "", "", 0
    for frame in soup.find_all("div", {"class": "cardFrame"}):
        stars_on = len(frame.find_all("div", {"class": "cardStarOn"}))
        stars_off = len(frame.find_all("div", {"class": "cardStarOff"}))
        star_off = stars_on + stars_off
        power = frame.find("div", {"class": "cardPH"})
        damage = frame.find("div", {"class": "cardPDD"})
        ability = frame.find("div", {"class": "cardPower"})
        bonus_div = frame.find("div", {"class": "cardBonus"})
        image = frame.find("img", {"class": lambda value: value != "clan" and value != "cardClanPict"})
        clan_pict = frame.find("img", {"class": "cardClanPict"})
        levels.append(ScrapedLevel(
            stars=stars_on,
            power=_int(power.text if power else ""),
            damage=_int(damage.text if damage else ""),
            ability=_capacity_text(ability) if ability else "",
            image=image.get("src", "") if image else "",
        ))
        if bonus_div:
            bonus = _capacity_text(bonus_div)
        if clan_pict:
            clan_image = clan_pict.get("src", "")

    levels.sort(key=lambda level: level.stars)
    bonus, night_bonus = _day_and_night_bonus(bonus)
    return ScrapedCard(id=card_id, name=name.strip(), faction=faction.strip(), star_off=star_off,
                       bonus=bonus, clan_image=clan_image, levels=levels,
                       night_ability=_night_ability(soup), night_bonus=night_bonus)


def to_official_json(cards: List[ScrapedCard]) -> Dict[str, dict]:
    """
    Même forme que l'historique jsonData_officiel.json (clé = nom, niveaux sous "1".."5"), plus id,
    clan_image, image par niveau, night_ability et night_bonus quand la carte en a. En cas d'homonymes, la
    première carte rencontrée est conservée.
    """
    data: Dict[str, dict] = {}
    for card in cards:
        if card.name in data:
            continue
        entry = {"id": card.id, "faction": card.faction, "starOff": card.star_off, "bonus": card.bonus, "clan_image": card.clan_image}
        if card.night_ability:
            entry["night_ability"] = card.night_ability
        if card.night_bonus:
            entry["night_bonus"] = card.night_bonus
        for level in card.levels:
            entry[str(level.stars)] = {"power": level.power, "damage": level.damage, "ability": level.ability, "image": level.image}
        data[card.name] = entry
    return data
