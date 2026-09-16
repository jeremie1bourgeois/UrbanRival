"""
Journal des effets (D2) : chaque round consigne, en français, ce que le moteur applique. Scénario de niveau 1 :
Amelia (allié, P3 D5, idx 2, 3 étoiles) contre Asporov (ennemi, P7 D3, idx 0, 4 étoiles), bonus -2 opp power des deux
côtés, abilities neutralisées sauf paramètre.
"""
import pytest

from src.core.domain.journal import Journal, note, recording
from tests.test_apply_capacity_lvl_1 import capacity, play


# --- Domaine ----------------------------------------------------------------------------------

def test_note_outside_a_recording_is_a_no_op():
    note(None, "test", "rien")   # ne lève pas


def test_recording_captures_entries_with_the_side_of_the_card(template_game):
    amelia, asporov = template_game.ally.cards[2], template_game.enemy.cards[0]
    journal = Journal(ally_card=amelia, enemy_card=asporov)

    with recording(journal):
        note(amelia, "pouvoir", "un effet")
        note(asporov, "bonus", "un autre")
        note(None, "round", "issue")

    assert journal.entries == [
        {"side": "ally", "card": "Amelia", "source": "pouvoir", "text": "un effet"},
        {"side": "enemy", "card": "Asporov", "source": "bonus", "text": "un autre"},
        {"side": None, "card": None, "source": "round", "text": "issue"},
    ]


def test_recording_is_cleared_afterwards(template_game):
    amelia = template_game.ally.cards[2]
    journal = Journal(ally_card=amelia, enemy_card=template_game.enemy.cards[0])
    with recording(journal):
        pass
    note(amelia, "pouvoir", "trop tard")

    assert journal.entries == []


# --- Rejeu d'un round -------------------------------------------------------------------------

def texts(game):
    return [entry["text"] for entry in game.history[-1].log]


def test_round_log_is_stored_in_the_round_and_serialized(template_game):
    play(template_game)

    log = template_game.history[-1].log
    assert log and all(set(entry) == {"side", "card", "source", "text"} for entry in log)
    assert template_game.to_dict()["history"][-1]["log"] == log


def test_round_outcome_is_logged(template_game):
    play(template_game, ally_pillz=6)   # Amelia 1 x 6 = 6 > Asporov 5 x 1 = 5

    assert "Amelia gagne (6 > 5) : l'ennemi perd 5 vies (12 → 7)" in texts(template_game)


def test_tie_outcome_explains_the_tie_rule(template_game):
    play(template_game, ally_pillz=5)   # 5 = 5 ; Amelia 3 étoiles < Asporov 4

    assert "Égalité 5 à 5 : Amelia gagne (moins d'étoiles) : l'ennemi perd 5 vies (12 → 7)" in texts(template_game)


def test_stat_modifiers_are_logged_with_before_and_after(template_game):
    play(template_game, enemy_ability="Power +2")

    log = texts(template_game)   # ordre du moteur : cibles ally, puis both, puis enemy
    assert "Asporov : pouvoir « Power +2 » → puissance d'Asporov 7 → 9" in log
    assert "Amelia : bonus « -2 Opp Power, Min 1 » → puissance d'Asporov 9 → 7" in log
    assert "Asporov : bonus « -2 Opp Power, Min 1 » → puissance d'Amelia 3 → 1" in log


def test_attack_computation_fury_and_attack_modifiers_are_logged(template_game):
    amelia = template_game.ally.cards[2]
    amelia.ability, amelia.bonus = None, None
    template_game.enemy.cards[0].ability = capacity("Attack +5")
    template_game.enemy.cards[0].ability_description = "Attack +5"
    template_game.enemy.cards[0].bonus = None
    from src.schemas.game_schemas import ProcessRoundInput
    from src.core.use_cases.process_round import process_round
    process_round(template_game, ProcessRoundInput(player1_card_index=2, player1_pillz=4, player1_fury=True, player2_card_index=0, player2_pillz=1))

    log = texts(template_game)
    assert "Amelia : fury → dégâts 5 → 7" in log
    assert "Amelia : attaque = 3 × 4 pillz = 12" in log
    assert "Asporov : attaque = 7 × 1 pillz = 7" in log
    assert "Asporov : pouvoir « Attack +5 » → attaque d'Asporov 7 → 12" in log
