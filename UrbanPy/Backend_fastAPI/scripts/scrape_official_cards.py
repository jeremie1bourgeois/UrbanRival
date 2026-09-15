"""
Re-scrape toutes les cartes d'iclintz.com vers data/jsonData_officiel.json.
Usage (depuis UrbanPy/Backend_fastAPI) : python scripts/scrape_official_cards.py [--workers 4] [--output data/jsonData_officiel.json]
Les pages téléchargées sont mises en cache dans data/.scrape_cache/ (ignoré par git) : relancer reprend où on en était.
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.adapters.scraping.iclintz import (  # noqa: E402
    BASE_URL, CLANS_INDEX_URL, CLAN_URL, card_links, clan_ids, parse_card_page, to_official_json,
)

CACHE_DIR = os.path.join(ROOT, "data", ".scrape_cache")
USER_AGENT = "Mozilla/5.0 (UrbanRival open-source engine; card data refresh)"


def fetch(session: requests.Session, url: str, attempts: int = 4) -> str:
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as error:
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)
            print(f"  nouvel essai {attempt}/{attempts} pour {url} ({error})", flush=True)
    raise RuntimeError("unreachable")


def cached_card_page(session: requests.Session, card_id: int) -> str:
    path = os.path.join(CACHE_DIR, f"card_{card_id}.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    html = fetch(session, f"{BASE_URL}/characters/card.php?ID={card_id}")
    with open(path, "w", encoding="utf-8") as file:
        file.write(html)
    time.sleep(0.1)   # politesse
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default=os.path.join(ROOT, "data", "jsonData_officiel.json"))
    args = parser.parse_args()
    os.makedirs(CACHE_DIR, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    ids = clan_ids(fetch(session, CLANS_INDEX_URL))
    print(f"{len(ids)} clans", flush=True)
    card_ids = []
    for clan_id in ids:
        links = card_links(fetch(session, CLAN_URL.format(clan_id=clan_id)))
        for link in links:
            card_id = int(re.search(r"ID=(\d+)", link).group(1))
            if card_id not in card_ids:
                card_ids.append(card_id)
        print(f"  clan {clan_id}: {len(links)} cartes (total {len(card_ids)})", flush=True)

    cards, failures = [], []
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(cached_card_page, session, card_id): card_id for card_id in card_ids}
        for done, future in enumerate(as_completed(futures), start=1):
            card_id = futures[future]
            try:
                cards.append(parse_card_page(future.result(), card_id))
            except Exception as error:  # noqa: BLE001 - on veut continuer et lister les échecs
                failures.append((card_id, str(error)))
            if done % 250 == 0 or done == len(card_ids):
                print(f"  {done}/{len(card_ids)} pages ({time.time() - started:.0f}s)", flush=True)

    cards.sort(key=lambda card: card.id)
    data = to_official_json(cards)
    duplicates = len(cards) - len(data)
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    factions = sorted({card.faction for card in cards})
    print(f"\n{len(data)} cartes écrites dans {args.output} ({duplicates} homonymes ignorés, {len(failures)} échecs)")
    print(f"{len(factions)} clans : {', '.join(factions)}")
    for card_id, error in failures[:20]:
        print(f"  échec carte {card_id}: {error}")


if __name__ == "__main__":
    main()
