"""
Corpus de non-régression du moteur : chaque famille de scénarios (scenarios.py) jouée par le moteur de référence et
enregistrée sous la forme du contrat — deck compilé, état, actions, état suivant, issue du round. Tout moteur qui
implémente le contrat — le port compilé — doit reproduire chaque entrée : c'est le test différentiel, à relancer à
chaque changement de règle.
Les fichiers se régénèrent à l'identique (générateurs déterministes) et ne sont pas versionnés ; seuls leurs digests
le sont (data/engine_digests.json) : tests/test_engine_golden.py les recalcule, tout changement de règle s'y
voit et se régénère consciemment (scripts/build_engine_corpus.py).
Format, par famille : <famille>.decks.json (liste de decks, dataclasses.asdict) et <famille>.jsonl (une entrée par
ligne : id, deck = indice dans la liste, state, ally_action, enemy_action, next_state, outcome) ; vocabulary.json une
fois. Les entrées sont écrites en JSON canonique (clés triées, sans espace) : c'est sur ces lignes que porte le digest.
Les deux autres fonctions du contrat, legal_actions et terminal, ont leur fichier : regles.jsonl (une entrée par
état : state, legal_actions de chaque camp, terminal), sur des états qui parcourent tout leur domaine (rules_states).
"""
import hashlib
import json
import os
from dataclasses import asdict
from itertools import product
from typing import Dict, Iterator, List, Optional

from src.core.domain.game import NB_ROUNDS
from src.core.engine.contract import (CLANS, CONDITIONS, EFFECT_KINDS, HOWS, TARGETS, TYPES, Deck, PlayerState,
                                      State)
from src.core.engine.reference import legal_actions, play, terminal
from src.core.engine.scenarios import FAMILIES

RULES = "regles"
RULES_STOCK = 15   # stocks de pillz et de vies parcourus : au-delà des 12 de départ, que Dope ou Heal peuvent dépasser

VOCABULARY = {"hows": HOWS, "types": TYPES, "conditions": CONDITIONS, "targets": TARGETS, "clans": CLANS,
              "effect_kinds": EFFECT_KINDS}


def canonical(record) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def family_entries(name: str, decks: List[Deck]) -> Iterator[dict]:
    """Joue chaque scénario de la famille ; les decks distincts sont ajoutés à `decks`, référencés par indice."""
    index: Dict[Deck, int] = {}
    ids = set()
    for scenario in FAMILIES[name]():
        if scenario.label in ids:
            raise ValueError(f"identifiant en double dans la famille {name} : {scenario.label}")
        ids.add(scenario.label)
        deck_id = index.get(scenario.deck)
        if deck_id is None:
            deck_id = index[scenario.deck] = len(decks)
            decks.append(scenario.deck)
        next_state, outcome = play(scenario.deck, scenario.state, scenario.ally_action, scenario.enemy_action)
        yield {"id": scenario.label, "deck": deck_id, "state": asdict(scenario.state),
               "ally_action": list(scenario.ally_action), "enemy_action": list(scenario.enemy_action),
               "next_state": asdict(next_state),
               "outcome": {"ally": list(outcome.ally), "enemy": list(outcome.enemy)}}


def family_summary(name: str, directory: Optional[str] = None) -> dict:
    """Effectifs et digest sha256 de la famille (entrées puis decks) ; écrit ses deux fichiers si `directory` est donné."""
    digest = hashlib.sha256()
    decks: List[Deck] = []
    entries = 0
    out = open(os.path.join(directory, f"{name}.jsonl"), "w", encoding="utf-8") if directory else None
    try:
        for entry in family_entries(name, decks):
            line = canonical(entry)
            digest.update(line.encode("utf-8") + b"\n")
            entries += 1
            if out:
                out.write(line + "\n")
    finally:
        if out:
            out.close()
    for deck in decks:
        digest.update(canonical(asdict(deck)).encode("utf-8") + b"\n")
    if directory:
        with open(os.path.join(directory, f"{name}.decks.json"), "w", encoding="utf-8") as file:
            json.dump([asdict(deck) for deck in decks], file, ensure_ascii=False)
    return {"entries": entries, "decks": len(decks), "sha256": digest.hexdigest()}


def rules_states() -> Iterator[State]:
    """
    Chaque main (masque des cartes jouées) avec chaque stock de pillz de 0 à RULES_STOCK, le camp ennemi prenant le
    masque complémentaire et le stock inverse ; puis chaque round de 1 à NB_ROUNDS + 1 avec chaque paire de vies de 0
    à RULES_STOCK.
    """
    for mask, pillz in product(range(16), range(RULES_STOCK + 1)):
        played = tuple(bool(mask >> index & 1) for index in range(4))
        yield State(1, True, PlayerState(12, pillz, played, ()),
                    PlayerState(12, RULES_STOCK - pillz, tuple(not card for card in played), ()), None)
    for nb_turn, ally_life, enemy_life in product(range(1, NB_ROUNDS + 2), range(RULES_STOCK + 1), range(RULES_STOCK + 1)):
        yield State(nb_turn, True, PlayerState(ally_life, 12, (False,) * 4, ()),
                    PlayerState(enemy_life, 12, (False,) * 4, ()), None)


def rules_summary(directory: Optional[str] = None) -> dict:
    """Effectif et digest sha256 des entrées de règles ; écrit regles.jsonl si `directory` est donné."""
    digest = hashlib.sha256()
    entries = 0
    out = open(os.path.join(directory, f"{RULES}.jsonl"), "w", encoding="utf-8") if directory else None
    try:
        for state in rules_states():
            line = canonical({"state": asdict(state), "terminal": terminal(state),
                              "legal_actions": {side: [list(action) for action in legal_actions(state, side)]
                                                for side in ("ally", "enemy")}})
            digest.update(line.encode("utf-8") + b"\n")
            entries += 1
            if out:
                out.write(line + "\n")
    finally:
        if out:
            out.close()
    return {"entries": entries, "sha256": digest.hexdigest()}


def vocabulary_digest() -> str:
    return hashlib.sha256(canonical(VOCABULARY).encode("utf-8")).hexdigest()


def read_digests(path: str) -> dict:
    if not os.path.exists(path):
        return {"vocabulary": None, "families": {}}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_corpus(directory: str, digests_path: str, families=None) -> dict:
    """
    Écrit vocabulary.json, regles.jsonl et les fichiers de chaque famille demandée dans `directory`, puis met à jour
    le fichier des digests (les familles non demandées gardent le leur) ; renvoie les digests.
    """
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "vocabulary.json"), "w", encoding="utf-8") as file:
        json.dump(VOCABULARY, file, ensure_ascii=False)
    digests = read_digests(digests_path)
    digests["vocabulary"] = vocabulary_digest()
    for name in (families or FAMILIES):
        digests["families"][name] = family_summary(name, directory)
    digests["families"] = {name: digests["families"][name] for name in FAMILIES if name in digests["families"]}
    digests["rules"] = rules_summary(directory)
    with open(digests_path, "w", encoding="utf-8") as file:
        json.dump(digests, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return digests
