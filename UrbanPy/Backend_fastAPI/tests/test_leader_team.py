"""
Leaders : l'ability « Team: X » du Leader s'applique à chaque carte jouée de l'équipe (Leader compris),
uniquement s'il est le seul Leader en main. Scénario : Agustino (allié idx 0) devient Leader ;
Amelia (idx 2, P3 D5, ability neutralisée) contre Asporov (idx 0, P7 D3, ability neutralisée), 1 pillz chacun.
Bonus -2 opp power actifs (3 All Stars alliés restants, 3 ennemis).
"""
import copy

import pytest

from src.core.domain.card import Card
from src.core.domain.capacity import Capacity
from src.core.parsing.capacity_parser import parse_capacity
from src.core.use_cases.process_round import process_round
from src.schemas.game_schemas import ProcessRoundInput

AGUSTINO, ALLISON, AMELIA, ASPOROV = 0, 1, 2, 0


def ability(text):
    parsed = parse_capacity(text)
    assert parsed.supported, parsed.reason
    return parsed.capacity


@pytest.fixture
def game(template_game):
    template_game.ally.cards[AMELIA].ability = None
    template_game.enemy.cards[ASPOROV].ability = None
    leader = template_game.ally.cards[AGUSTINO]
    leader.faction = "Leader"
    leader.ability = ability("Team: Power +2")
    return template_game


def play(game, ally_index=AMELIA, enemy_index=ASPOROV, turn=True):
    game.turn = turn
    process_round(game, ProcessRoundInput(player1_card_index=ally_index, player1_pillz=1, player2_card_index=enemy_index, player2_pillz=1))
    return game.ally.cards[ally_index], game.enemy.cards[enemy_index]


def test_team_ability_applies_to_a_team_mate(game):
    amelia, _ = play(game)

    assert amelia.power_fight == 3 + 2 - 2


def test_team_ability_applies_to_the_leader_itself(game):
    agustino, _ = play(game, ally_index=AGUSTINO)

    assert agustino.power_fight == 6 + 2 - 2
    assert agustino.ability_fight is None          # « Team: » n'est pas une ability de carte


def test_two_leaders_cancel_the_team_ability(game):
    game.ally.cards[ALLISON].faction = "Leader"

    amelia, _ = play(game)

    assert amelia.power_fight == 3 - 2


def test_two_copies_of_the_same_leader_cancel_the_team_ability(game):
    # Modes avec doublons : deux exemplaires du même Leader s'annulent comme deux Leaders différents
    # (confirmé par l'utilisateur, 2026-09-21).
    game.ally.cards[ALLISON] = copy.deepcopy(game.ally.cards[AGUSTINO])

    amelia, _ = play(game)

    assert amelia.power_fight == 3 - 2


def test_team_ability_keeps_its_own_conditions(game):
    game.ally.cards[AGUSTINO].ability = ability("Team: Courage: Power +3")

    amelia, _ = play(game, turn=False)             # l'allié ne joue pas en premier : pas de courage

    assert amelia.power_fight == 3 - 2


def test_leader_benefits_from_its_own_conditional_team_when_condition_met(game):
    # Ambre : « Team: Courage: Power +3 ». Le Leader joué lui-même, en premier (courage actif), profite du bonus.
    game.ally.cards[AGUSTINO].ability = ability("Team: Courage: Power +3")

    agustino, _ = play(game, ally_index=AGUSTINO, turn=True)   # le Leader joue en premier -> courage

    assert agustino.power_fight == 6 + 3 - 2


def test_team_level_1_effect_goes_through_the_same_pipeline(game):
    game.ally.cards[AGUSTINO].ability = ability("Team: Cancel Opp. Damage Modif.")
    game.enemy.cards[ASPOROV].ability = ability("Damage +2")

    _, asporov = play(game)

    assert asporov.damage_fight == 3


def test_leader_slot_is_consumed_after_the_round(game):
    amelia, _ = play(game)

    assert amelia.leader_fight is None


def test_leader_fight_round_trips_through_json(game):
    card = game.ally.cards[AMELIA]
    card.leader_fight = Capacity(target="ally", types=["power"], value=2, borne=-1)

    restored = Card.from_dict_template(card.to_dict())

    assert restored.leader_fight.to_dict() == card.leader_fight.to_dict()


# --- Autres abilities de Leader ------------------------------------------------------------------

def test_per_round_leader_ability_applies_every_round_win_or_lose(game):
    game.ally.cards[AGUSTINO].ability = ability("+1 Pillz Per Round")   # Morphun

    play(game)                                                          # Amelia perd

    assert game.ally.pillz == 12 + 1


def test_opp_pillz_per_round_leader_ability(game):
    game.ally.cards[AGUSTINO].ability = ability("-1 Opp. Pillz, Per Round, Min 4")   # Eklore

    play(game)

    assert game.enemy.pillz == 12 - 1


def test_team_cancel_players_damage_mod_cancels_both_sides(game):
    game.ally.cards[AGUSTINO].ability = ability("Team: Cancel Players Dam. Mod.")   # Vholt-like
    game.ally.cards[AMELIA].ability = ability("Damage +2")
    game.enemy.cards[ASPOROV].ability = ability("-3 Opp Damage, Min 1")

    amelia, asporov = play(game)

    assert (amelia.damage_fight, asporov.damage_fight) == (5, 3)


def test_tie_break_leader_wins_every_attack_tie(game):
    game.ally.cards[AGUSTINO].ability = ability("Tie-break")   # Solomon
    game.ally.cards[ALLISON].stars = 5                          # 5 étoiles > Asporov 4 : Allison perdrait l'égalité
    game.ally.cards[ALLISON].ability = None
    game.ally.cards[ALLISON].power = 7                          # 7 - 2 = 5 = Asporov 7 - 2 : égalité d'attaque

    allison, asporov = play(game, ally_index=ALLISON)

    assert (allison.attack, asporov.attack) == (5, 5)
    assert allison.win is True                                  # sans Tie-break, Asporov (4 étoiles) gagnerait


def test_counter_attack_leader_makes_his_team_play_second_in_the_first_round(game):
    # Ashigaru : son camp joue en second au premier round (utilisateur, 2026-09-21)
    game.ally.cards[AGUSTINO].ability = ability("Counter-attack")
    game.ally.cards[AMELIA].ability = ability("Reprisal: Power +2")
    game.enemy.cards[ASPOROV].ability = ability("Courage: Power +2")

    amelia, asporov = play(game, turn=True)                     # même si c'était le tour de l'allié

    assert (amelia.power_fight, asporov.power_fight) == (3 + 2 - 2, 7 + 2 - 2)
    assert game.turn is True                                    # puis alternance classique : l'allié joue en premier au round 2


def test_counter_attack_leader_does_not_change_the_order_after_the_first_round(game):
    game.ally.cards[AGUSTINO].ability = ability("Counter-attack")
    game.ally.cards[AMELIA].ability = ability("Courage: Power +2")
    game.nb_turn = 2

    amelia, _ = play(game, turn=True)                           # round 2, tour de l'allié : Ashigaru ne l'inverse plus

    assert amelia.power_fight == 3 + 2 - 2


def test_limitless_leader_removes_maximums_and_zeroes_minimums_of_abilities(game):
    # Fractal : « the maximums on abilities are cancelled and the minimums are replaced by the minimum 0. This effect does not apply to bonuses. »
    game.ally.cards[AGUSTINO].ability = ability("Limitless")
    game.ally.cards[AMELIA].ability = ability("-3 Opp Damage, Min 2")

    _, asporov = play(game)

    assert asporov.damage_fight == 0                            # 3 - 3, plancher 0 au lieu de 2
    assert asporov.power_fight == 7 - 2                         # le bonus -2 opp power min 1 n'est pas touché


def test_limitless_does_not_apply_to_bonuses(game):
    game.ally.cards[AGUSTINO].ability = ability("Limitless")
    game.enemy.cards[ASPOROV].power = 2                         # bonus allié -2 opp power, min 1 : 2 -> 1, pas 0

    _, asporov = play(game)

    assert asporov.power_fight == 1

