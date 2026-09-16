"""
Bonus Oculus « Infiltrated » : l'Oculus adopte le bonus du clan majoritaire parmi les autres cartes de la main
(hors Oculus et Leader) et compte comme membre de ce clan pour l'activation du bonus ; égalité -> aucun bonus.
Scénario : main alliée du template (4 All Stars, bonus -2 opp power, abilities neutralisées) modifiée carte par
carte ; Asporov (ennemi, P7, ability neutralisée) subit ou non le bonus adopté.
"""
import pytest

from src.core.parsing.capacity_parser import parse_capacity
from src.core.use_cases.process_round import process_round
from src.schemas.game_schemas import ProcessRoundInput

AGUSTINO, ALLISON, AMELIA, ASHLEY, ASPOROV = 0, 1, 2, 3, 0
MONTANA_BONUS = "-12 Opp Attack, Min 8"


def capacity(text):
    parsed = parse_capacity(text)
    assert parsed.supported, parsed.reason
    return parsed.capacity


@pytest.fixture
def game(template_game):
    for card in template_game.ally.cards:
        card.ability = None
    template_game.enemy.cards[ASPOROV].ability = None
    return template_game


def make(card, faction, bonus_text):
    card.faction = faction
    card.bonus = capacity(bonus_text)


def play(game, ally_index, enemy_pillz=1):
    process_round(game, ProcessRoundInput(player1_card_index=ally_index, player1_pillz=1, player2_card_index=ASPOROV, player2_pillz=enemy_pillz))
    return game.ally.cards[ally_index], game.enemy.cards[ASPOROV]


def test_oculus_adopts_the_bonus_of_the_other_clan(game):
    make(game.ally.cards[AMELIA], "Oculus", "Infiltrated")           # 1 Oculus + 3 All Stars

    _, asporov = play(game, AMELIA)

    assert asporov.power_fight == 7 - 2


def test_oculus_adopts_the_majority_clan(game):
    make(game.ally.cards[AMELIA], "Oculus", "Infiltrated")
    make(game.ally.cards[AGUSTINO], "Montana", MONTANA_BONUS)         # 1 Oculus + 1 Montana + 2 All Stars

    _, asporov = play(game, AMELIA)

    assert asporov.power_fight == 7 - 2                              # All Stars, pas Montana


def test_oculus_gets_nothing_on_a_tie(game):
    make(game.ally.cards[AMELIA], "Oculus", "Infiltrated")
    make(game.ally.cards[AGUSTINO], "Montana", MONTANA_BONUS)
    make(game.ally.cards[ALLISON], "Junkz", "Attack +8")              # 1 Oculus + Montana + Junkz + All Stars

    _, asporov = play(game, AMELIA)

    assert asporov.power_fight == 7


def test_oculus_counts_as_a_member_for_the_adopted_clan_activation(game):
    make(game.ally.cards[AMELIA], "Oculus", "Infiltrated")
    make(game.ally.cards[AGUSTINO], "Montana", MONTANA_BONUS)
    make(game.ally.cards[ALLISON], "Leader", "Cancel Leader")
    make(game.ally.cards[ASHLEY], "Leader", "Cancel Leader")          # Montana seul + Oculus : le bonus Montana s'active

    _, asporov = play(game, AGUSTINO, enemy_pillz=2)                  # Agustino (Montana) joue ; Asporov 7 x 2 = 14

    assert asporov.attack == 8                                        # 14 - 12, min 8


def test_lone_clan_card_without_oculus_has_no_bonus(game):
    make(game.ally.cards[AGUSTINO], "Montana", MONTANA_BONUS)         # Montana seul, 3 All Stars

    _, asporov = play(game, AGUSTINO, enemy_pillz=2)

    assert asporov.attack == 14


def test_a_hand_of_oculus_only_has_no_bonus(game):
    for card in game.ally.cards:
        make(card, "Oculus", "Infiltrated")

    amelia, asporov = play(game, AMELIA)

    assert (amelia.bonus_fight, asporov.power_fight) == (None, 7)
