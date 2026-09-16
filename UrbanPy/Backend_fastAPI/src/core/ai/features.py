"""
Les « critères » que l'IA regarde pour juger un coup (carte + pillz + fury).

L'idée, en une phrase : pour chaque coup jouable, on calcule une poignée de nombres simples (la puissance de la
carte, les pillz qu'on y met, l'avance en vie…), on les multiplie chacun par un **poids**, et on additionne.
Le coup au plus gros total est celui que l'IA joue. L'entraînement ne fait qu'une chose : chercher les bons poids.

C'est volontairement transparent : à la fin de l'entraînement, on peut lire les poids et dire « l'IA a appris à
garder ses pillz quand elle mène ». Un réseau de neurones jouerait sans doute mieux, mais ne dirait rien.

Chaque critère est ramené à une échelle comparable (grosso modo entre -1 et 1), sinon les critères aux grands
nombres écraseraient les autres.
"""
from dataclasses import dataclass
from typing import Dict, List

from src.core.ai.opponent import FURY_COST, Pick
from src.core.domain.game import NB_ROUNDS, Game

FURY_DAMAGE = 2          # la fury ajoute 2 dégâts pour 3 pillz
MAX_POWER = 8.0          # ordres de grandeur pour ramener les critères à une échelle commune
MAX_DAMAGE = 8.0
MAX_LIFE = 12.0
MAX_PILLZ = 12.0
MAX_STARS = 5.0
JUST_ENOUGH_MARGIN = 8.0   # au-delà de 8 points d'attaque d'avance, on considère qu'on a surpayé


@dataclass(frozen=True)
class Feature:
    name: str
    explanation: str


#: Les critères, dans l'ordre. `explanation` sert à la documentation et à l'affichage des poids appris.
FEATURES: List[Feature] = [
    Feature("biais", "Constante. Sert de point de repère : décale tous les scores sans rien différencier."),
    Feature("puissance", "Puissance de la carte jouée. Plus c'est haut, plus l'attaque est forte à pillz égales."),
    Feature("degats", "Dégâts de la carte jouée, fury comprise. C'est ce qu'on retire à l'adversaire si on gagne."),
    Feature("attaque_estimee", "Puissance x pillz misées : l'attaque avant bonus et pouvoirs."),
    Feature("pillz_misees", "Pillz dépensées sur ce coup, fury comprise. Un poids négatif = l'IA apprend l'économie."),
    Feature("pillz_gardees", "Pillz restantes après le coup. Un poids positif = l'IA garde des munitions."),
    Feature("fury", "1 si la fury est utilisée, 0 sinon. Coûte 3 pillz pour +2 dégâts."),
    Feature("coup_fatal", "1 si ces dégâts suffisent à mettre l'adversaire à 0 vie : le coup gagne la partie."),
    Feature("degats_gaspilles", "Dégâts au-delà de ce qu'il faut pour tuer. Frapper à 8 un adversaire à 2 vie en gâche 6."),
    Feature("avance_en_vie", "Ma vie moins la sienne. Positif = je mène, et je peux me permettre de défendre."),
    Feature("rounds_restants", "Rounds encore à jouer, celui-ci compris. Au dernier round, garder des pillz ne sert à rien."),
    Feature("etoiles", "Étoiles de la carte. En cas d'égalité d'attaque, la carte avec le MOINS d'étoiles gagne."),
    Feature("mise_relative", "Part des pillz disponibles engagée sur ce coup. Mesure l'excès, indépendamment du stock."),
    Feature("carte_gardee_forte", "Force de la meilleure carte gardée en main. Élevé = on n'a pas grillé son atout."),
    # --- Ce que l'adversaire peut faire. Dans Urban Rivals sa main est visible : une IA qui l'ignore joue
    # --- à l'aveugle, et c'est ce qui plafonnait la première version.
    Feature("pillz_adverses", "Pillz restantes à l'adversaire. S'il est à sec, une petite mise suffit à gagner le round."),
    Feature("avantage_pillz", "Mes pillz après ce coup, moins les siennes. C'est la vraie monnaie de la partie."),
    Feature("menace_adverse", "Force de sa meilleure carte encore en main. Élevé = il garde un gros coup."),
    Feature("rapport_attaque", "Mon attaque rapportée à l'attaque maximale qu'il peut sortir. Au-dessus de 0,5 je suis favori."),
    Feature("degats_risques", "Dégâts que je prends si je perds ce round (sa meilleure carte). C'est la mise en face."),
    Feature("danger_de_mort", "1 si sa meilleure carte peut me tuer ce round. Il faut alors défendre, pas attaquer."),
    Feature("enjeu_favorable", "Mes dégâts rapportés à la somme des deux. Au-dessus de 0,5 le round vaut plus pour moi que pour lui."),
    Feature("rapport_attaque_probable", "Comme rapport_attaque, mais en supposant qu'il étale ses pillz sur les rounds restants au lieu de tout miser. Plus réaliste face à un joueur prudent."),
    # --- « Juste ce qu'il faut ». Une note linéaire préfère toujours miser plus ; ces deux critères-ci lui
    # --- donnent de quoi exprimer le contraire : passer de peu, et ne pas surpayer.
    Feature("marge_attaque", "Mon attaque moins son attaque probable. Négatif = je perds le round, très positif = je surpaye."),
    Feature("juste_suffisant", "1 si je passe devant lui sans excès (marge faible mais positive). C'est le coup idéal : gagner au plus juste."),
]

FEATURE_NAMES: List[str] = [feature.name for feature in FEATURES]
FEATURE_COUNT = len(FEATURES)


def _side_players(state: Game, side: str):
    return (state.ally, state.enemy) if side == "ally" else (state.enemy, state.ally)


def feature_vector(state: Game, side: str, pick: Pick) -> List[float]:
    """Les critères d'un coup, dans l'ordre de FEATURES. Fonction pure et sans allocation superflue (appelée
    une fois par coup jouable, soit ~100 fois par décision)."""
    me, opponent = _side_players(state, side)
    card = me.cards[pick.card_index]

    bet = (pick.pillz - 1) + (FURY_COST if pick.fury else 0)     # pillz réellement dépensées (la 1re est gratuite)
    damage = card.damage + (FURY_DAMAGE if pick.fury else 0)
    kept = me.pillz - bet
    rounds_left = max(1, NB_ROUNDS - state.nb_turn + 1)

    overkill = max(0, damage - opponent.life)
    others = [other for index, other in enumerate(me.cards) if index != pick.card_index and not other.played]
    best_kept = max((other.power * other.damage for other in others), default=0)

    # Ce que l'adversaire peut opposer, avec les cartes qu'il n'a pas encore jouées.
    opponent_cards = [card_ for card_ in opponent.cards if not card_.played]
    opp_best_power = max((card_.power for card_ in opponent_cards), default=0)
    opp_best_damage = max((card_.damage for card_ in opponent_cards), default=0)
    opp_best_value = max((card_.power * card_.damage for card_ in opponent_cards), default=0)

    my_attack = card.power * pick.pillz
    opp_max_attack = opp_best_power * (opponent.pillz + 1)      # s'il mise tout sur sa meilleure carte
    attack_ratio = my_attack / (my_attack + opp_max_attack) if (my_attack + opp_max_attack) > 0 else 0.5
    stake_ratio = damage / (damage + opp_best_damage) if (damage + opp_best_damage) > 0 else 0.5

    # Hypothèse plus réaliste : il répartit ses pillz sur les rounds qui restent (c'est ce que fait l'heuristique,
    # et c'est ce que fait un humain prudent). Miser contre son attaque *maximale* revient à toujours surpayer.
    opp_likely_attack = opp_best_power * (opponent.pillz / rounds_left + 1)
    likely_ratio = my_attack / (my_attack + opp_likely_attack) if (my_attack + opp_likely_attack) > 0 else 0.5

    # Gagner le round de justesse vaut autant que le gagner largement, mais coûte bien moins cher. Une somme
    # pondérée ne peut pas inventer ce « juste au-dessus » toute seule : on le lui fournit tout fait.
    margin = my_attack - opp_likely_attack
    just_enough = 1.0 if 0 <= margin <= JUST_ENOUGH_MARGIN else 0.0

    return [
        1.0,
        card.power / MAX_POWER,
        damage / MAX_DAMAGE,
        my_attack / (MAX_POWER * MAX_PILLZ),
        bet / MAX_PILLZ,
        kept / MAX_PILLZ,
        1.0 if pick.fury else 0.0,
        1.0 if damage >= opponent.life else 0.0,
        overkill / MAX_DAMAGE,
        (me.life - opponent.life) / MAX_LIFE,
        rounds_left / NB_ROUNDS,
        card.stars / MAX_STARS,
        bet / max(1.0, float(me.pillz)),
        best_kept / (MAX_POWER * MAX_DAMAGE),
        opponent.pillz / MAX_PILLZ,
        (kept - opponent.pillz) / MAX_PILLZ,
        opp_best_value / (MAX_POWER * MAX_DAMAGE),
        attack_ratio,
        opp_best_damage / MAX_DAMAGE,
        1.0 if opp_best_damage >= me.life else 0.0,
        stake_ratio,
        likely_ratio,
        max(-1.0, min(1.0, margin / (MAX_POWER * MAX_PILLZ))),
        just_enough,
    ]


def describe_weights(weights: List[float], top: int = 6) -> str:
    """Rend les poids appris lisibles : les critères qui pèsent le plus, du plus fort au plus faible."""
    pairs = sorted(zip(FEATURES, weights), key=lambda pair: abs(pair[1]), reverse=True)
    lines = []
    for feature, weight in pairs[:top]:
        direction = "recherche" if weight > 0 else "évite"
        lines.append(f"  {weight:+7.3f}  {feature.name:<20} l'IA {direction} ce critère — {feature.explanation}")
    return "\n".join(lines)


def weights_as_dict(weights: List[float]) -> Dict[str, float]:
    return dict(zip(FEATURE_NAMES, weights))
