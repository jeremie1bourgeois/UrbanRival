"""Cherche dans la collection du compte Urban Rivals « jere'm » (data/collection/collection_jerem.json) les cartes
dont le pouvoir correspond à un motif, pour composer les decks de docs/ORACLE.md avec des cartes possédées.

    .venv/bin/python scripts/collection_lookup.py "Stop Opp. Ability" --exclude GHEIST,Roots,Nightmare,Piranas
    .venv/bin/python scripts/collection_lookup.py "Copy: Opp. Damage" --clan Pussycats,Montana
    .venv/bin/python scripts/collection_lookup.py . --clan Leader          # toutes les cartes d'un clan

Le motif est une expression régulière (insensible à la casse) appliquée au pouvoir **au niveau possédé** ; les cartes
dont le pouvoir n'est débloqué qu'à un niveau supérieur sont listées à part (« à monter »). Les pouvoirs viennent de
data/jsonData_officiel.json (anglais). La collection a été relevée passivement depuis la page « Ma collection » du
site (DOM, filtre « Seulement possédés »), sans appel API : voir docs/ORACLE.md § 2.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "jsonData_officiel.json"
COLLECTION_PATH = ROOT / "data" / "collection" / "collection_jerem.json"


def load():
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    coll = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))["cards"]
    owned: dict[str, set[int]] = {}
    for tile in coll:
        owned.setdefault(tile["name"], set()).add(tile["level"])
    return db, owned


def max_level(card: dict) -> int:
    return max(int(k) for k in card if k.isdigit())


def is_unlocked(ability: str) -> bool:
    return not ability.startswith("Ability at Level") and ability != "No Ability"


def lookup(db, owned, pattern, clans=None, exclude=None):
    """Retourne (actives, à_monter) : listes de (nom, clan, niveau possédé, niveau max, puissance, dégâts, pouvoir, bonus)."""
    rx = re.compile(pattern, re.IGNORECASE)
    active, to_level = [], []
    for name, levels in owned.items():
        card = db.get(name)
        if card is None:
            continue
        clan = card["faction"]
        if clans and clan not in clans or exclude and clan in exclude:
            continue
        level = max(levels)
        top = max_level(card)
        ability_now = card[str(level)]["ability"]
        row = lambda lvl, ability: (name, clan, level, top, card[str(lvl)]["power"], card[str(lvl)]["damage"], ability, card["bonus"])
        if is_unlocked(ability_now) and rx.search(ability_now):
            active.append(row(level, ability_now))
        elif rx.search(card[str(top)]["ability"]):
            to_level.append(row(level, card[str(top)]["ability"]))
    key = lambda r: (r[3], r[0])
    return sorted(active, key=key), sorted(to_level, key=key)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pattern", help="expression régulière sur le pouvoir (ex. 'Stop Opp\\. Bonus', 'Poison', '.')")
    parser.add_argument("--clan", help="clans à garder, séparés par des virgules")
    parser.add_argument("--exclude", help="clans à écarter, séparés par des virgules")
    args = parser.parse_args()
    split = lambda s: {c.strip() for c in s.split(",")} if s else None
    db, owned = load()
    active, to_level = lookup(db, owned, args.pattern, split(args.clan), split(args.exclude))
    fmt = lambda r: f"  {r[0]:18} {r[1]:14} niv {r[2]}/{r[3]}  {r[4]}/{r[5]}  {r[6]:50}  bonus : {r[7]}"
    print(f"Pouvoir actif au niveau possédé ({len(active)}) :")
    print("\n".join(map(fmt, active)) or "  (aucune)")
    if to_level:
        print(f"\nÀ monter de niveau pour débloquer le pouvoir ({len(to_level)}) :")
        print("\n".join(map(fmt, to_level)))


if __name__ == "__main__":
    main()
