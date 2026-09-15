from src.core.domain.card import Card


def test_fury_survives_a_json_round_trip(template_game):
    card = template_game.ally.cards[0]
    card.fury = True

    assert Card.from_dict_template(card.to_dict()).fury is True
