"""
Invariants du moteur sur les scénarios du corpus combinatoire : ce qu'un port doit respecter aussi, indépendamment
des valeurs enregistrées. La propriété miroir (camps échangés et premier joueur inversé -> état miroir) n'est pas
vraie partout : le moteur traite la carte alliée avant la carte ennemie, et quand les deux camps portent des effets
à plancher sur la même stat (« Cards », niveau 2), le même joueur (vie / pillz, niveau 3) ou enregistrent des effets
persistants (ordre de la liste, niveau 4), l'ordre compte. Les scénarios où cela se produit sont épinglés ci-dessous :
toute nouvelle asymétrie fait échouer le test, toute règle d'ordre décidée les fera disparaître (REGLES § 5).
"""
from itertools import islice

import pytest

from src.core.engine.contract import EFFECT_KINDS, State
from src.core.engine.reference import play
from src.core.engine.scenarios import FAMILIES

pytestmark = pytest.mark.corpus

FULLY_MIRRORED = ("planchers", "persistants", "leaders", "oculus", "combat", "aleatoire")
SAMPLE_EVERY = 10    # solo et interactions : un scénario sur dix (aucune asymétrie trouvée sur l'ensemble)

KNOWN_ASYMMETRIES = frozenset({
    # niveau 2 : « Cards » à plancher des deux côtés, l'allié réduit d'abord
    "planchers/damage/cartes -2 Cards Damage, Min 1 contre cartes Support: -1 Cards Damage, Min 3/r1",
    "planchers/damage/cartes -2 Cards Damage, Min 4 contre cartes -4 Cards Damage, Min 0/r1",
    "planchers/damage/cartes -2 Cards Damage, Min 4 contre cartes -4 Cards Damage, Min 1/r1",
    "planchers/damage/cartes -2 Cards Damage, Min 4 contre cartes Support: -1 Cards Damage, Min 0/r1",
    "planchers/damage/cartes -2 Cards Damage, Min 4 contre cartes Support: -1 Cards Damage, Min 3/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 0 contre cartes -2 Cards Damage, Min 4/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 0 contre cartes -4 Cards Damage, Min 1/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 0 contre cartes Support: -1 Cards Damage, Min 3/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 1 contre cartes -2 Cards Damage, Min 4/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 1 contre cartes -4 Cards Damage, Min 0/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 1 contre cartes Support: -1 Cards Damage, Min 0/r1",
    "planchers/damage/cartes -4 Cards Damage, Min 1 contre cartes Support: -1 Cards Damage, Min 3/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 0 contre cartes -2 Cards Damage, Min 4/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 0 contre cartes -4 Cards Damage, Min 1/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 0 contre cartes Support: -1 Cards Damage, Min 3/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 3 contre cartes -2 Cards Damage, Min 1/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 3 contre cartes -2 Cards Damage, Min 4/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 3 contre cartes -4 Cards Damage, Min 0/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 3 contre cartes -4 Cards Damage, Min 1/r1",
    "planchers/damage/cartes Support: -1 Cards Damage, Min 3 contre cartes Support: -1 Cards Damage, Min 0/r1",
    # niveau 3 : vie / pillz du même joueur touchées par les deux cartes, avec plancher (allié d'abord)
    "aleatoire/partie-83/round-2/coup-1",
    "aleatoire/partie-106/round-1/coup-2",
    "aleatoire/partie-188/round-3/coup-3",
    # niveau 4 : les effets persistants sont enregistrés dans l'ordre allié puis ennemi
    "aleatoire/partie-199/round-2/coup-2",
    "aleatoire/partie-199/round-4/coup-3",
})


def _originals(family):
    """Les scénarios de la famille hors miroirs déjà présents (le miroir est recalculé ici)."""
    return (scenario for scenario in FAMILIES[family]() if not scenario.label.endswith("/miroir"))


def _mirror_state(state: State) -> State:
    last = state.last_round
    return State(nb_turn=state.nb_turn, ally_first=not state.ally_first, ally=state.enemy, enemy=state.ally,
                 last_round=None if last is None else (last[1], last[0], not last[2]))


def _has_counter_attack(deck) -> bool:
    from src.core.engine.contract import HOWS
    return any(card.ability is not None and HOWS[card.ability.how] == "counter_attack"
               for hand in (deck.ally, deck.enemy) for card in hand)


@pytest.mark.parametrize("family", list(FAMILIES))
def test_next_state_invariants(family):
    for scenario in islice(FAMILIES[family](), 0, None, 5):
        state, ally_action, enemy_action = scenario.state, scenario.ally_action, scenario.enemy_action
        next_state, outcome = play(scenario.deck, state, ally_action, enemy_action)
        label = scenario.label
        assert next_state.nb_turn == state.nb_turn + 1, label
        assert next_state.ally.life >= 0 and next_state.enemy.life >= 0, label
        assert next_state.ally.pillz >= 0 and next_state.enemy.pillz >= 0, label
        assert next_state.ally.played == tuple(played or i == ally_action.card for i, played in enumerate(state.ally.played)), label
        assert next_state.enemy.played == tuple(played or i == enemy_action.card for i, played in enumerate(state.enemy.played)), label
        assert outcome.ally.win != outcome.enemy.win, label
        assert next_state.last_round == (ally_action.card, enemy_action.card, outcome.ally.win), label
        if not (state.nb_turn == 1 and _has_counter_attack(scenario.deck)):
            assert next_state.ally_first == (not state.ally_first), label
        for side in (outcome.ally, outcome.enemy):
            assert side.power >= 0 and side.damage >= 0 and side.attack >= 0, label
        for player in (next_state.ally, next_state.enemy):
            kinds = [kind for kind, _, _ in player.effects]
            assert all(0 <= kind < len(EFFECT_KINDS) for kind in kinds), label
            assert len(kinds) == len(set(kinds)), f"{label} : deux effets de même sorte"


@pytest.mark.parametrize("family", list(FAMILIES))
def test_play_is_deterministic(family):
    for scenario in islice(FAMILIES[family](), 0, None, 25):
        first = play(scenario.deck, scenario.state, scenario.ally_action, scenario.enemy_action)
        assert play(scenario.deck, scenario.state, scenario.ally_action, scenario.enemy_action) == first, scenario.label


def test_mirror_symmetry_holds_except_on_the_known_asymmetries():
    asymmetric = set()
    for family in FAMILIES:
        scenarios = _originals(family) if family in FULLY_MIRRORED else islice(_originals(family), 0, None, SAMPLE_EVERY)
        for scenario in scenarios:
            direct, outcome = play(scenario.deck, scenario.state, scenario.ally_action, scenario.enemy_action)
            mirror = scenario.mirrored()
            mirrored, mirrored_outcome = play(mirror.deck, mirror.state, mirror.ally_action, mirror.enemy_action)
            if _mirror_state(mirrored) != direct or (mirrored_outcome.enemy, mirrored_outcome.ally) != (outcome.ally, outcome.enemy):
                asymmetric.add(scenario.label)
    assert asymmetric == KNOWN_ASYMMETRIES
