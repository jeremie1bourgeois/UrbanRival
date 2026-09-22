"""
Multiplicateurs de capacités (champ `how`) partagés par les niveaux du moteur.
Chaque fonction reçoit (game, player1, player2, card1, card2) où player1/card1 sont le propriétaire
de la capacité et player2/card2 son adversaire, et renvoie le facteur appliqué à `value`.
"""
from src.core.use_cases.clan import clan_for_bonus

def _one(game, player1, player2, card1, card2) -> int:
    return 1


def _growth(game, player1, player2, card1, card2) -> int:
    return game.nb_turn


def _degrowth(game, player1, player2, card1, card2) -> int:
    return 5 - game.nb_turn


def _support(game, player1, player2, card1, card2) -> int:
    # Un Oculus rallié au clan compte (combat 1347602 : Freaks ×3 + Dark Majestic -> Support ×4) ; les doublons aussi
    return sum(1 for c in player1.cards if clan_for_bonus(player1, c) == clan_for_bonus(player1, card1))


def _equalizer(game, player1, player2, card1, card2) -> int:
    return card2.stars


def _brawl(game, player1, player2, card1, card2) -> int:
    return sum(1 for c in player2.cards if clan_for_bonus(player2, c) == clan_for_bonus(player2, card2))


def _nb_damage_opp(game, player1, player2, card1, card2) -> int:
    return card2.damage


def _nb_power_opp(game, player1, player2, card1, card2) -> int:
    return card2.power


def _nb_damage_inflicted(game, player1, player2, card1, card2) -> int:
    """Dégâts réellement infligés par la carte ce round (0 si elle a perdu) ; valable après resolve_combat."""
    return card1.damage_fight if card1.win else 0


def _nb_life_lost(game, player1, player2, card1, card2) -> int:
    """Vies perdues depuis le début de la partie ; jamais négatif si un soin a dépassé la vie de départ (REGLES 3.14)."""
    return max(0, player1.start_life - player1.life)


def _nb_pillz_lost(game, player1, player2, card1, card2) -> int:
    return max(0, player1.start_pillz - player1.pillz)


def _nb_pillz_left(game, player1, player2, card1, card2) -> int:
    """Pillz restantes « avant de mettre des pillz sur ton perso (sans compter la Pillz gratuite) » (glossaire 66)."""
    return player1.pillz + (card1.pillz_fight - 1) + (3 if card1.fury else 0)   # process_round a déjà déduit la mise


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
    "nb_pow_opp": _nb_power_opp,
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
