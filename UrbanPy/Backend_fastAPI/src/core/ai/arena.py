"""
Banc d'essai des adversaires automatiques (feuille de route E4) : faire jouer deux stratégies l'une contre
l'autre sur des mains tirées au hasard et compter les victoires. Les deux camps échangent de place d'une partie
à l'autre : l'allié joue en premier, ce qui est un avantage, et il ne faut pas l'attribuer toujours au même.

Tout passe par l'API moteur pure (`engine`) : aucune partie n'est écrite sur le disque.
"""
import math
import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from src.adapters.repositories.card_repository import official_card_catalogue
from src.core.ai import engine
from src.schemas.game_schemas import GameResult

Strategy = Callable[..., engine.Pick]
Hand = List[Tuple[str, int]]
CARDS_PER_HAND = 4


@dataclass
class MatchResult:
    """Bilan d'un affrontement, du point de vue de la première stratégie."""
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self) -> float:
        """Taux de victoire, les nulles comptant pour une demi-partie."""
        return (self.wins + 0.5 * self.draws) / self.games if self.games else 0.0

    def confidence_interval(self, z: float = 1.96) -> Tuple[float, float]:
        """
        Intervalle de Wilson du taux de victoire (95 % par défaut). Sur 60 parties il fait ±13 points, sur 100
        ±10, sur 1 000 ±3 : aucune comparaison de stratégies ne se lit sans lui (docs/IA.md, étape 5).
        """
        n = self.games
        if n == 0:
            return (0.0, 1.0)
        p, z2 = self.win_rate, z * z
        centre = (p + z2 / (2 * n)) / (1 + z2 / n)
        half_width = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
        return (max(0.0, centre - half_width), min(1.0, centre + half_width))

    def __str__(self) -> str:
        low, high = self.confidence_interval()
        return (f"{self.wins}V / {self.losses}D / {self.draws}N sur {self.games} parties "
                f"({self.win_rate:.1%} [{low:.1%} ; {high:.1%}])")


def play_game(hands: Tuple[Hand, Hand], ally_strategy: Strategy, enemy_strategy: Strategy,
              rng: random.Random) -> GameResult:
    """
    Une partie ELO complète entre deux stratégies (14 vies, premier joueur tiré au sort puis alterné,
    carte du premier joueur révélée au second). Renvoie le résultat du point de vue de l'allié.
    """
    state = engine.elo_game(*hands, rng)
    final = engine.play_out(state, {"ally": ally_strategy, "enemy": enemy_strategy}, rng, in_place=True)
    return engine.result(final)


def duel(first: Strategy, second: Strategy, nb_games: int, rng: random.Random,
         hands_factory: Callable[[random.Random], Tuple[Hand, Hand]] = None) -> MatchResult:
    """
    `nb_games` parties entre deux stratégies, côtés échangés une partie sur deux, mains tirées au hasard
    (les deux joueurs reçoivent la même main : le duel mesure les stratégies, pas la qualité des decks).
    """
    hands_factory = hands_factory or mirrored_hands
    result = MatchResult()
    for game_number in range(nb_games):
        first_is_ally = game_number % 2 == 0
        ally, enemy = (first, second) if first_is_ally else (second, first)
        outcome = play_game(hands_factory(rng), ally, enemy, rng)
        if outcome is GameResult.DRAW:
            result.draws += 1
        elif (outcome is GameResult.ALLY) == first_is_ally:
            result.wins += 1
        else:
            result.losses += 1
    return result


def round_robin(strategies: dict, nb_games: int, rng: random.Random) -> dict:
    """Toutes les stratégies deux à deux ; renvoie {(nom, nom adverse): MatchResult}."""
    names = sorted(strategies)
    return {(first, second): duel(strategies[first], strategies[second], nb_games, rng)
            for index, first in enumerate(names) for second in names[index + 1:]}


def mirrored_hands(rng: random.Random) -> Tuple[Hand, Hand]:
    """La même main pour les deux joueurs : le duel ne dépend alors que des décisions."""
    hand = random_hand(rng)
    return hand, hand


def random_hands(rng: random.Random) -> Tuple[Hand, Hand]:
    """Deux mains tirées indépendamment."""
    return random_hand(rng), random_hand(rng)


def random_hand(rng: random.Random, nb_cards: int = CARDS_PER_HAND) -> Hand:
    """
    Main de deux clans à deux cartes : les bonus de clan sont actifs des deux côtés (règle : au moins deux
    cartes du clan), ce qui rend les parties représentatives. Cartes entièrement gérées par le moteur seulement.
    """
    clans = _playable_cards_by_clan()
    chosen = rng.sample(sorted(clans), 2)
    hand = []
    for clan in chosen:
        for name, levels in rng.sample(clans[clan], nb_cards // 2):
            hand.append((name, rng.choice(levels)))
    return hand


_CLAN_CACHE: dict = {}


def _playable_cards_by_clan() -> dict:
    """
    {clan: [(nom, [niveaux jouables]), ...]} pour les cartes dont le bonus et toutes les abilities sont gérés
    par le moteur, dans un clan qui compte assez de cartes pour en tirer deux. Les Leaders sont exclus
    (pas de bonus de clan, et un Leader unique change les règles du round : à traiter à part).
    """
    if _CLAN_CACHE:
        return _CLAN_CACHE
    for card in official_card_catalogue():
        if card["faction"] == "Leader" or not card["bonus_supported"]:
            continue
        levels = [level["stars"] for level in card["levels"] if level["ability_supported"]]
        if levels:
            _CLAN_CACHE.setdefault(card["faction"], []).append((card["name"], levels))
    for clan, cards in list(_CLAN_CACHE.items()):
        if len(cards) < CARDS_PER_HAND // 2:
            del _CLAN_CACHE[clan]
    return _CLAN_CACHE
