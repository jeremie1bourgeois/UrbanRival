"""
Multiplicateurs de capacités (champ `how`) partagés par les niveaux du moteur.
Chaque fonction reçoit (game, player1, player2, card1, card2) où player1/card1 sont le propriétaire
de la capacité et player2/card2 son adversaire, et renvoie le facteur appliqué à `value`.
"""
MAX_LIFE = 12   # vie de départ ; à paramétrer avec la partie si elle devient variable
MAX_PILLZ = 12


def _one(game, player1, player2, card1, card2) -> int:
    return 1


def _growth(game, player1, player2, card1, card2) -> int:
    return game.nb_turn


def _degrowth(game, player1, player2, card1, card2) -> int:
    return 5 - game.nb_turn


def _support(game, player1, player2, card1, card2) -> int:
    return sum(1 for c in player1.cards if c.faction == card1.faction)


def _equalizer(game, player1, player2, card1, card2) -> int:
    return card2.stars


def _brawl(game, player1, player2, card1, card2) -> int:
    return sum(1 for c in player2.cards if c.faction == card2.faction)


def _nb_damage_opp(game, player1, player2, card1, card2) -> int:
    return card2.damage


def _nb_damage_inflicted(game, player1, player2, card1, card2) -> int:
    """Dégâts réellement infligés par la carte ce round (0 si elle a perdu) ; valable après resolve_combat."""
    return card1.damage_fight if card1.win else 0


def _nb_life_lost(game, player1, player2, card1, card2) -> int:
    return MAX_LIFE - player1.life


def _nb_pillz_lost(game, player1, player2, card1, card2) -> int:
    return MAX_PILLZ - player1.pillz


def _nb_pillz_left(game, player1, player2, card1, card2) -> int:
    return player1.pillz


def _nb_life_left(game, player1, player2, card1, card2) -> int:
    return player1.life


MULTIPLIERS = {
    "": _one,
    "growth": _growth,
    "degrowth": _degrowth,
    "support": _support,
    "equalizer": _equalizer,
    "brawl": _brawl,
    "nb_dam_opp": _nb_damage_opp,
    "nb_damage": _nb_damage_inflicted,
    "nb_life_lost": _nb_life_lost,
    "nb_pillz_lost": _nb_pillz_lost,
    "nb_pillz_left": _nb_pillz_left,
    "nb_life_left": _nb_life_left,
}


def multiplier(how: str, game, player1, player2, card1, card2) -> int:
    func = MULTIPLIERS.get(how)
    if func is None:
        raise ValueError(f"Invalid how: {how!r}")
    return func(game, player1, player2, card1, card2)
