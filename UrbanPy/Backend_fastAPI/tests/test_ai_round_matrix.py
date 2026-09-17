"""
Matrice de round rapide (`src/core/ai/round_matrix.py`) : pour un état et un couple de cartes, l'issue de toutes
les mises sans rejouer le round entier à chaque cellule. La règle : **identique au moteur, cellule à cellule**
(`engine.step` reste la seule source de vérité) ; le raccourci ne s'autorise que là où aucune capacité ne lit la
mise, sinon repli sur le moteur.
"""
import pytest

from src.core.ai import engine, round_matrix, solver
from src.core.domain.game import NB_ROUNDS


def endgame(ally, enemy, life, pillz, ally_first, rounds_left=1, history=None):
    state = engine.new_game(ally, enemy, life=1, pillz=0, ally_first=ally_first)
    state.nb_turn = NB_ROUNDS - rounds_left + 1
    state.ally.life, state.enemy.life = life
    state.ally.pillz, state.enemy.pillz = pillz
    if history is not None:
        state.history.extend(history)
    return state


def engine_values(state, first, card_first, card_second, leaf):
    """La référence : chaque cellule rejouée par le moteur."""
    second = engine.other(first)
    return {(own, theirs): leaf(engine.next_state(state, first, own, theirs))
            for own in engine.legal_actions(state, first) if own.card_index == card_first
            for theirs in engine.legal_actions(state, second) if theirs.card_index == card_second}


def reward_for_ally(state):
    return engine.reward(state, "ally")


def test_last_round_values_match_the_engine_cell_by_cell():
    """Wardog (8/2) contre Lilith (5/4), 4 pillz chacun : 7 × 7 cellules (mises 0-4, fury avec 0 ou 1)."""
    state = endgame([("Wardog", 2)], [("Lilith", 3)], life=(5, 5), pillz=(4, 4), ally_first=True)

    fast = round_matrix.values(state, "ally", 0, 0, reward_for_ally)

    assert fast == engine_values(state, "ally", 0, 0, reward_for_ally)
    assert len(fast) == 7 * 7


def test_the_shortcut_replays_the_round_at_most_once_per_outcome_class(monkeypatch):
    """Sans capacité lisant la mise, le moteur ne rejoue le round que par classe (vainqueur × fury × fury) : ≤ 8 fois."""
    calls = []
    real_step = engine.step
    monkeypatch.setattr(engine, "step", lambda *args, **kwargs: calls.append(1) or real_step(*args, **kwargs))
    state = endgame([("Wardog", 2)], [("Lilith", 3)], life=(5, 5), pillz=(4, 4), ally_first=True)

    round_matrix.values(state, "ally", 0, 0, reward_for_ally)

    assert 0 < len(calls) <= 8


def test_next_states_of_a_third_round_match_the_engine_on_their_canonical_key():
    """Round 3 : les feuilles sont des états de round 4 ; leur clé canonique (vies, pillz, cartes, historique) est identique."""
    state = endgame([("Wardog", 2), ("Meroo", 1)], [("Lilith", 3), ("Natrang", 3)],
                    life=(6, 6), pillz=(5, 5), ally_first=False, rounds_left=2)

    for card_first in (0, 1):
        for card_second in (0, 1):
            fast = round_matrix.values(state, "enemy", card_first, card_second, solver.canonical_key)
            assert fast == engine_values(state, "enemy", card_first, card_second, solver.canonical_key)


# Mains à bonus actifs (deux cartes du clan) et pouvoirs variés : modificateurs d'attaque bornés, Attack +8,
# Support, Stops, Protection, Cancel, poison, vie adverse, Leader « Team », Growth / Courage / Equalizer.
HANDS = {
    "Montana contre Junkz": ([("Pino", 2), ("Lino Borsa", 3)], [("Nobrocybix Cr", 2), ("Acid DC Cr", 3)]),
    "Uppers contre Sakrohm": ([("Mo DiFalco", 3), ("Armanda Cr", 3)], [("Venus", 4), ("Venus", 3)]),
    "Rescue contre Raptors": ([("Dr L Home", 3), ("Larry", 2)], [("Capri Cr", 3), ("Capri Cr", 2)]),
    "GHEIST contre Skeelz": ([("Lilith", 3), ("Brutox", 2)], [("Danae", 2), ("Redra", 2)]),
    "Freaks contre Berzerk": ([("Dacha Macha", 3), ("Boris Cr", 2)], [("Kawamashi Cr", 2), ("Melanie", 2)]),
    "Nightmare contre Pussycats": ([("Elixir", 3), ("Elixir", 2)], [("Shawoman Cr", 3), ("Alice", 2)]),
    "Leader Hugo contre Leader Ambre": ([("Hugo", 2), ("Acid DC Cr", 3)], [("Ambre", 2), ("Sephora", 3)]),
    "All Stars contre All Stars (partie d'exemple)": ([("Agustino", 2), ("Allison", 3)], [("Asporov", 4), ("Amelia", 3)]),
}


@pytest.mark.parametrize("hands", HANDS.values(), ids=list(HANDS))
@pytest.mark.parametrize("ally_first", [True, False], ids=["allié premier", "ennemi premier"])
def test_every_cell_matches_the_engine_on_real_hands(hands, ally_first):
    """Round 3 à 4 pillz, vies basses (KO possibles) puis hautes, avec un round précédent perdu par l'allié (Revenge)."""
    from src.core.domain.round import Round
    previous = Round()
    previous.ally.card_index, previous.enemy.card_index, previous.ally.win, previous.enemy.win = 0, 0, False, True
    first = "ally" if ally_first else "enemy"
    for life in ((4, 5), (12, 12)):
        state = endgame(*hands, life=life, pillz=(4, 4), ally_first=ally_first, rounds_left=2, history=[previous])
        for card_first in (0, 1):
            for card_second in (0, 1):
                fast = round_matrix.values(state, first, card_first, card_second, solver.canonical_key)
                assert fast == engine_values(state, first, card_first, card_second, solver.canonical_key), \
                    (life, card_first, card_second)


SENSITIVE = {
    "Recover (pillz récupérées selon la mise)": ("Strygia", 2),          # Victory Or Defeat : +1 Pillz
    "Tune Out": ("Cosmohnuts", None),
    "Killshot": ("Vansaar", 2),                                          # Team: Killshot: -2 Opp. Life Min 4
    "+1 Pillz Per Round": ("Morphun", 2),
}


def test_hands_whose_capacities_read_the_bet_are_detected():
    """Ces capacités lisent la mise ou les pillz : le raccourci est interdit, le moteur rejoue chaque cellule."""
    assert not round_matrix.bet_sensitive(endgame([("Wardog", 2)], [("Lilith", 3)], (5, 5), (4, 4), True))
    for card in (("Strygia", 2), ("Vansaar", 2), ("Morphun", 2)):
        assert round_matrix.bet_sensitive(endgame([card, ("Wardog", 2)], [("Lilith", 3)], (5, 5), (4, 4), True)), card


def test_a_persistent_pillz_effect_makes_the_state_sensitive():
    from src.core.domain.effect import PersistentEffect
    state = endgame([("Wardog", 2)], [("Lilith", 3)], (5, 5), (4, 4), True)
    state.enemy.effect_list.append(PersistentEffect("dope", 1, 5))

    assert round_matrix.bet_sensitive(state)


def test_sensitive_hands_still_match_the_engine_cell_by_cell():
    """Le repli : identité triviale, mais elle garde le contrat quel que soit le chemin."""
    state = endgame([("Strygia", 2), ("Wardog", 2)], [("Lilith", 3), ("Natrang", 3)],
                    life=(6, 6), pillz=(4, 4), ally_first=True, rounds_left=2)

    fast = round_matrix.values(state, "ally", 0, 1, solver.canonical_key)

    assert fast == engine_values(state, "ally", 0, 1, solver.canonical_key)
