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


# --- Niveau 1 et conditions -------------------------------------------------------------------

def test_stops_name_the_stopper(template_game):
    play(template_game, enemy_ability="Stop Opp. Bonus")

    assert "Amelia : bonus « -2 Opp Power, Min 1 » stoppé par Asporov (pouvoir « Stop Opp. Bonus »)" in texts(template_game)


def test_cycle_stops_are_logged_as_a_cycle(template_game):
    play(template_game, ally_ability="Stop Opp. Ability", enemy_ability="Stop Opp. Ability")

    assert "Amelia : pouvoir « Stop Opp. Ability » stoppé (cycle de Stops)" in texts(template_game)


def test_copy_names_what_is_copied(template_game):
    play(template_game, ally_ability="Copy: Opp. Bonus")

    log = texts(template_game)
    assert "Amelia : pouvoir « Copy: Opp. Bonus » copie le bonus d'Asporov « -2 Opp Power, Min 1 »" in log
    assert "Amelia : copie du bonus d'Asporov « -2 Opp Power, Min 1 » → puissance d'Asporov 7 → 5" in log or \
           "Amelia : copie du bonus d'Asporov « -2 Opp Power, Min 1 » → puissance d'Asporov 5 → 3" in log


def test_cancel_and_protection_are_logged(template_game):
    play(template_game, ally_ability="Cancel Opp. Power Modif.", enemy_ability="Protection: Damage")

    log = texts(template_game)
    assert "Amelia : pouvoir « Cancel Opp. Power Modif. » annule les modifications de puissance d'Asporov" in log
    assert "Asporov : pouvoir « Protection: Damage » protège ses dégâts" in log


def test_impose_is_logged_as_a_stat_change(template_game):
    play(template_game, ally_ability="Power Impose")

    assert "Amelia : pouvoir « Power Impose » → puissance d'Asporov 7 → 3" in texts(template_game)


def test_unmet_condition_and_inactive_bonus_are_logged(template_game):
    template_game.enemy.cards[0].faction = "Rescue"                       # Asporov seul Rescue... avec Serafina : 2 -> il faut l'isoler
    template_game.enemy.cards[3].faction = "Junkz"
    play(template_game, ally_ability="Courage: Power +2", turn=False)

    log = texts(template_game)
    assert "Amelia : pouvoir « Courage: Power +2 » inactif (condition Courage non remplie)" in log
    assert "Asporov : bonus « -2 Opp Power, Min 1 » inactif (une seule carte Rescue en main)" in log


def test_killshot_condition_is_logged_both_ways(template_game):
    play(template_game, ally_ability="Killshot: +3 Life", ally_pillz=10)

    assert "Amelia : Killshot remplie (10 ≥ 2 × 5)" in texts(template_game)

    game = template_game
    game.ally.cards[2].played = game.enemy.cards[0].played = False
    play(game, ally_ability="Killshot: +3 Life", ally_pillz=9)

    assert "Amelia : Killshot non remplie (9 < 2 × 5) : pouvoir « Killshot: +3 Life » inactif" in texts(game)


def test_tune_out_is_logged(template_game):
    play(template_game, ally_bonus="Tune Out", ally_pillz=2)

    assert "Tune Out : le round se résout aux pillz (Amelia 2, Asporov 1)" in texts(template_game)


# --- Fin de round (niveau 3) et effets persistants (niveau 4) ----------------------------------

def test_end_of_round_life_and_pillz_effects_are_logged(template_game):
    play(template_game, ally_ability="+3 Life", enemy_ability="Defeat: +2 Pillz", ally_pillz=6)   # Amelia gagne

    log = texts(template_game)
    assert "Amelia : pouvoir « +3 Life » → vie de l'allié 12 → 15" in log
    assert "Asporov : pouvoir « Defeat: +2 Pillz » → pillz de l'ennemi 12 → 14" in log


def test_recover_and_reanimate_are_logged(template_game):
    play(template_game, ally_ability="Defeat: Recover 2 Pillz Out Of 3", ally_pillz=4, enemy_pillz=8)   # Amelia perd, 4 posées -> 2

    assert "Amelia : pouvoir « Defeat: Recover 2 Pillz Out Of 3 » → pillz de l'allié 9 → 11" in texts(template_game)

    game = template_game
    game.ally.life = 3
    game.ally.cards[2].played = game.enemy.cards[0].played = False
    play(game, ally_ability="Reanimate +2 Life", ally_pillz=1, enemy_pillz=2)   # Amelia perd 3 -> 0, réanimée

    assert "Amelia : pouvoir « Reanimate +2 Life » réanime l'allié → vie 0 → 2" in texts(game)


def test_instant_ko_is_logged(template_game):
    play(template_game, ally_ability="Fatal Killshot", ally_pillz=10)

    assert "Amelia : pouvoir « Fatal Killshot » met l'ennemi KO" in texts(template_game)


def test_persistent_effects_registration_tick_and_suspension_are_logged(template_game):
    from tests.test_apply_capacity_lvl_4 import play as play4
    game = template_game
    for player in (game.ally, game.enemy):
        for card in player.cards:
            card.ability = None
            card.ability_description = ""
    game.enemy.cards[2].ability_description = "Cancel Opp. Life Modif."

    play4(game, 1, ally_ability="Poison 2, Min 1", ally_pillz=6)
    assert "Amelia : pouvoir « Poison 2, Min 1 » → poison 2 (min 1) sur l'ennemi" in texts(game)

    play4(game, 2, enemy_ability="Cancel Opp. Life Modif.", enemy_pillz=2)
    assert "poison 2 sur l'ennemi suspendu ce round (Annul)" in texts(game)

    play4(game, 3, enemy_pillz=5)
    assert "poison 2 → vie de l'ennemi 7 → 5" in texts(game)
