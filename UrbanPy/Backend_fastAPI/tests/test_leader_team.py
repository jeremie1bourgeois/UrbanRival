"""
Leaders : l'ability « Team: X » du Leader s'applique à chaque carte jouée de l'équipe (Leader compris),
uniquement s'il est le seul Leader en main. Scénario : Agustino (allié idx 0) devient Leader ;
Amelia (idx 2, P3 D5, ability neutralisée) contre Asporov (idx 0, P7 D3, ability neutralisée), 1 pillz chacun.
Bonus -2 opp power actifs (3 All Stars alliés restants, 3 ennemis).
"""
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


def test_team_ability_keeps_its_own_conditions(game):
    game.ally.cards[AGUSTINO].ability = ability("Team: Courage: Power +3")

    amelia, _ = play(game, turn=False)             # l'allié ne joue pas en premier : pas de courage

    assert amelia.power_fight == 3 - 2


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
