from src.core.domain.game import Game
from src.core.domain.round import Round


def test_two_games_do_not_share_history():
    first, second = Game(), Game()

    first.history.append(Round())

    assert second.history == []


def test_two_games_do_not_share_players():
    first, second = Game(), Game()

    first.ally.life = 3

    assert second.ally.life != 3
    assert first.ally is not second.ally
