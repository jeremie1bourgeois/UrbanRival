import copy
from collections import Counter
from src.core.domain.round import Round
from src.core.domain.capacity import Capacity
from src.core.domain.card import Card, FIGHT_SLOTS
from src.core.domain.player import Player
from src.schemas.game_schemas import ProcessRoundInput
from src.core.domain.game import Game, NB_ROUNDS
from src.core.domain.journal import Journal, note, recording
import src.core.use_cases.apply_capacity_lvl_1 as fct_lvl_1
import src.core.use_cases.apply_capacity_lvl_2 as fct_lvl_2
import src.core.use_cases.apply_capacity_lvl_3 as fct_lvl_3
import src.core.use_cases.apply_capacity_lvl_4 as fct_lvl_4

def process_round(game: Game, round_data: ProcessRoundInput) -> None:
    player1_card = game.ally.cards[round_data.player1_card_index]
    player2_card = game.enemy.cards[round_data.player2_card_index]
    journal = Journal(ally_card=player1_card, enemy_card=player2_card)
    with recording(journal):
        _process_round(game, round_data)
    game.history[-1].log = journal.entries


def _process_round(game: Game, round_data: ProcessRoundInput) -> None:
    try:
        # Mise à jour des pillz
        game.ally.pillz -= ((round_data.player1_pillz - 1) + 3 * round_data.player1_fury) # -1 car 1 pillz est toujours consommée
        game.enemy.pillz -= ((round_data.player2_pillz - 1) + 3 * round_data.player2_fury) # -1 car 1 pillz est toujours consommée

        # Récupérer les cartes sélectionnées
        player1_card = game.ally.cards[round_data.player1_card_index]
        player2_card = game.enemy.cards[round_data.player2_card_index]

        # Initialiser les données de combat
        init_fight_data(player1_card, round_data.player1_pillz, round_data.player1_fury)
        init_fight_data(player2_card, round_data.player2_pillz, round_data.player2_fury)

        # Bonus de clan : un Oculus « Infiltrated » adopte le bonus du clan majoritaire de la main ;
        # le bonus n'est actif que si la main compte au moins 2 cartes du clan (l'Oculus compris)
        apply_infiltrated_bonus(game.ally, player1_card)
        apply_infiltrated_bonus(game.enemy, player2_card)
        if not is_clan_bonus_active(game.ally, player1_card):
            player1_card.bonus_fight = None
        if not is_clan_bonus_active(game.enemy, player2_card):
            player2_card.bonus_fight = None

        # L'ability « Team: » d'un Leader unique s'applique à la carte jouée
        player1_card.leader_fight = leader_team_capacity(game.ally)
        player2_card.leader_fight = leader_team_capacity(game.enemy)
        apply_leader_modes(game, player1_card, player2_card)

        for card, is_ally, own_index, opp_index in ((player1_card, True, round_data.player1_card_index, round_data.player2_card_index),
                                                    (player2_card, False, round_data.player2_card_index, round_data.player1_card_index)):
            for slot in FIGHT_SLOTS:
                if not check_capacity_condition(game, getattr(card, slot), is_ally, own_index, opp_index):
                    setattr(card, slot, None)

        # Appliquer les effets de combat
        fct_lvl_1.apply_capacity_lvl_1(player1_card, player2_card)
        fct_lvl_2.apply_capacity_lvl_2(game, player1_card, player2_card, stats=("power", "damage"))

        # Appliquer les fury
        for card in (player1_card, player2_card):
            if card.fury:
                card.damage_fight += 2
                note(card, "fury", f"{card.name} : fury → dégâts {card.damage_fight - 2} → {card.damage_fight}")

        # Calculer les attaques
        for card, pillz in ((player1_card, round_data.player1_pillz), (player2_card, round_data.player2_pillz)):
            card.attack += card.power_fight * pillz
            note(card, "attaque", f"{card.name} : attaque = {card.power_fight} × {pillz} pillz = {card.attack}")

        # Modificateurs d'attaque, une fois l'attaque de base connue
        fct_lvl_2.apply_capacity_lvl_2(game, player1_card, player2_card, stats=("attack",))

        # Tune Out (Cosmohnuts) : « the Attack calculation is ignored and the winner is the player who bet the most Pillz »
        if consume_tune_out(player1_card) | consume_tune_out(player2_card):
            player1_card.attack, player2_card.attack = round_data.player1_pillz, round_data.player2_pillz

        # Killshot : la capacité n'agit que si l'attaque vaut au moins le double de l'attaque adverse
        apply_killshot_condition(player1_card, player2_card)
        apply_killshot_condition(player2_card, player1_card)
        apply_perfect_condition(player1_card, player2_card)
        apply_perfect_condition(player2_card, player1_card)

        # Créer une nouvelle instance de Round
        round_result = Round()
        round_result.ally.card_index = round_data.player1_card_index  # Stocker l'index de la carte
        round_result.enemy.card_index = round_data.player2_card_index  # Stocker l'index de la carte

        # Résoudre le combat
        resolve_combat(game, player1_card, player2_card, round_result)
        
        # Un joueur tombé à 0 vie a perdu avant les effets de fin de round, sauf s'il est réanimé
        if game.ally.life <= 0 or game.enemy.life <= 0:
            fct_lvl_3.apply_reanimate(game, player1_card, player2_card)
        if game.ally.life > 0 and game.enemy.life > 0:
            fct_lvl_3.apply_capacity_lvl_3(game, player1_card, player2_card)
            fct_lvl_4.apply_capacity_lvl_4(game, player1_card, player2_card)

        # Ajouter le round au history
        game.history.append(round_result)
    
        # Mettre à jour le tour
        player1_card.played = True
        player2_card.played = True

        game.nb_turn += 1
        game.turn = not game.turn

    except Exception as e:
        print(f"Exception in process_round: {e}")
        raise e


def resolve_combat(game: Game, player1_card: Card, player2_card: Card, round_result: Round):
    a1, a2 = player1_card.attack, player2_card.attack
    if a1 != a2:
        ally_wins, reason = a1 > a2, f"({max(a1, a2)} > {min(a1, a2)})"
    elif has_tie_break(player1_card) != has_tie_break(player2_card):        # Tie-break (Solomon) : gagne toute égalité
        ally_wins, reason = has_tie_break(player1_card), "(Tie-break)"
    elif player1_card.stars != player2_card.stars:                          # moins d'étoiles gagne
        ally_wins, reason = player1_card.stars < player2_card.stars, "(moins d'étoiles)"
    else:                                                                   # sinon celui qui a joué en premier
        ally_wins, reason = game.turn, "(a joué en premier)"

    winner, loser, loser_player, loser_side = ((player1_card, player2_card, game.enemy, "l'ennemi") if ally_wins
                                               else (player2_card, player1_card, game.ally, "l'allié"))
    before = loser_player.life
    loser_player.life = max(0, before - winner.damage_fight)
    round_result.ally.win, round_result.enemy.win = ally_wins, not ally_wins
    player1_card.win, player2_card.win = ally_wins, not ally_wins
    tie = f"Égalité {a1} à {a2} : " if a1 == a2 else ""
    note(None, "round", f"{tie}{winner.name} gagne {reason} : {loser_side} perd {winner.damage_fight} vies ({before} → {loser_player.life})")


# Conditions évaluées plus tard qu'au début du round : "stop" au niveau 1 (l'ability a-t-elle été stoppée ?),
# "killshot" et "perfect" après le calcul des attaques, les autres après le combat (niveau 3).
DEFERRED_CONDITIONS = {"stop", "killshot", "perfect", "defeat", "backlash", "victory_defeat"}


def check_capacity_condition(game: Game, capacity: Capacity, is_ally: bool, own_card_index: int, opp_card_index: int) -> bool:
    """
    Vérifie (et consomme) les conditions de début de round d'une capacité de combat.
    own_card_index / opp_card_index : index de la carte jouée par le joueur qui possède la capacité / par son adversaire.
    Retourne False si une condition n'est pas remplie ; les conditions différées au niveau 3 sont laissées en place.
    """
    if capacity is None or not capacity.effect_conditions:
        return True
    if "team" in capacity.effect_conditions:      # ability de Leader : jamais jouée comme ability de carte (voir leader_team_capacity)
        return False

    own_player, opp_player = (game.ally, game.enemy) if is_ally else (game.enemy, game.ally)
    last_round = game.history[-1] if game.history else None
    own_won_last_round = None if last_round is None else (last_round.ally.win if is_ally else last_round.enemy.win)
    plays_first = game.turn if is_ally else not game.turn

    checks = {
        "revenge": lambda: own_won_last_round is False,
        "confidence": lambda: own_won_last_round is True,
        "courage": lambda: plays_first,
        "reprisal": lambda: not plays_first,
        "symmetry": lambda: own_card_index == opp_card_index,
        "asymmetry": lambda: own_card_index != opp_card_index,
        "unison": lambda: hand_is_mono_clan(own_player, own_card_index),
        "disunion": lambda: not hand_is_mono_clan(own_player, own_card_index),
    }

    for condition in list(capacity.effect_conditions):
        if condition in checks:
            if not checks[condition]():
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("versus:"):                # « Versus <clans> » : au moins une carte du clan dans la main adverse
            clans = condition[len("versus:"):].split("|")   # (règle officielle : pas seulement la carte en face)
            if not any(card.faction in clans for card in opp_player.cards):
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("after:"):                 # « After <clans> » : ma carte du round précédent est du clan
            clans = condition[len("after:"):].split("|")    # (jamais au round 1 ; un Oculus infiltré ne compte pas)
            previous_index = None if last_round is None else (last_round.ally if is_ally else last_round.enemy).card_index
            if previous_index is None or own_player.cards[previous_index].faction not in clans:
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("infiltrated:"):           # ability d'Oculus : active seulement si le clan adopté est listé
            if clan_for_bonus(own_player, own_player.cards[own_card_index]) not in condition[len("infiltrated:"):].split("|"):
                return False
            capacity.effect_conditions.remove(condition)
        elif condition.startswith("bet"):
            if not _bet_condition_met(condition, own_player.cards[own_card_index].pillz_fight):
                return False
            capacity.effect_conditions.remove(condition)
        elif condition not in DEFERRED_CONDITIONS:
            raise ValueError(f"Invalid effect_conditions (check_capacity_condition): {capacity.effect_conditions}")
    return True


def leader_team_capacity(player: Player) -> Capacity:
    """
    Copie de l'ability « Team: X » du Leader de la main, à appliquer à la carte jouée — seulement si la main
    compte exactement un Leader (deux Leaders s'annulent : bonus « Cancel Leader »). None sinon.
    """
    leaders = [card for card in player.cards if card.faction == "Leader"]
    if len(leaders) != 1 or leaders[0].ability is None or "team" not in leaders[0].ability.effect_conditions:
        return None
    capacity = copy.deepcopy(leaders[0].ability)
    capacity.effect_conditions.remove("team")
    capacity.label = f"Leader {leaders[0].name} « {leaders[0].ability_description} »"
    return capacity


def has_tie_break(card: Card) -> bool:
    return any(getattr(card, slot) is not None and getattr(card, slot).how == "tie_break" for slot in FIGHT_SLOTS)


def consume_tune_out(card: Card) -> bool:
    """Retire un Tune Out (survivant à la phase des Stops) de la carte ; True s'il y en avait un."""
    found = False
    for slot in FIGHT_SLOTS:
        capacity = getattr(card, slot)
        if capacity is not None and capacity.how == "tune_out":
            setattr(card, slot, None)
            found = True
    return found


def apply_leader_modes(game: Game, player1_card: Card, player2_card: Card) -> None:
    """
    Modes de Leader lus avant les conditions : Counter-attack (Ashigaru) — « always plays second » : fixe l'ordre du
    round si un seul camp l'a ; Limitless (Fractal) — les maximums des abilities de l'équipe tombent, les minimums
    passent à 0 (pas les bonus).
    """
    modes = {}
    for card in (player1_card, player2_card):
        capacity = card.leader_fight
        if capacity is not None and capacity.how in ("counter_attack", "limitless"):
            modes[id(card)] = capacity.how
            card.leader_fight = None
    ally_counter, enemy_counter = modes.get(id(player1_card)) == "counter_attack", modes.get(id(player2_card)) == "counter_attack"
    if ally_counter != enemy_counter:
        game.turn = enemy_counter                  # l'allié joue en premier seulement si c'est l'ennemi qui a Ashigaru
    for card in (player1_card, player2_card):
        if modes.get(id(card)) == "limitless" and card.ability_fight is not None and card.ability_fight.borne != -1:
            card.ability_fight.borne = -1 if card.ability_fight.value > 0 else 0


def apply_killshot_condition(card: Card, opp_card: Card) -> None:
    """Consomme la condition « killshot » (attaque >= 2 x attaque adverse) ou désactive la capacité."""
    is_killshot = card.attack > 0 and card.attack >= 2 * opp_card.attack
    for slot in FIGHT_SLOTS:
        capacity = getattr(card, slot)
        if capacity is not None and "killshot" in capacity.effect_conditions:
            if is_killshot:
                capacity.effect_conditions.remove("killshot")
            else:
                setattr(card, slot, None)


def apply_perfect_condition(card: Card, opp_card: Card) -> None:
    """
    Consomme la condition « perfect » ou désactive la capacité. Règle officielle : l'écart d'attaque est strictement
    inférieur à la puissance de la carte (une pillz de moins n'aurait pas gagné). La victoire est exigée au niveau 3.
    """
    is_perfect = card.attack - opp_card.attack < card.power_fight
    for slot in FIGHT_SLOTS:
        capacity = getattr(card, slot)
        if capacity is not None and "perfect" in capacity.effect_conditions:
            if is_perfect:
                capacity.effect_conditions.remove("perfect")
            else:
                setattr(card, slot, None)


def _bet_condition_met(condition: str, pillz_fight: int) -> bool:
    """
    « bet>N » / « bet<N » (et la forme historique « bet N » = « bet>N ») comparent les pillz de la carte.
    Règle officielle (texte des cartes) : « including free Pillz and excluding Fury » -> pillz_fight tel quel.
    """
    bet = pillz_fight
    rest = condition[3:].strip()
    if rest.startswith("<"):
        return bet < int(rest[1:])
    return bet > int(rest.lstrip(">").strip())


def hand_is_mono_clan(player: Player, card_index: int) -> bool:
    """Unison (règle officielle) : la main contient exclusivement des cartes du clan de la carte jouée."""
    clan = player.cards[card_index].faction
    return all(card.faction == clan for card in player.cards)


MIN_CLAN_CARDS_FOR_BONUS = 2
OCULUS = "Oculus"
LEADER = "Leader"


def is_infiltrated(card: Card) -> bool:
    return card.faction == OCULUS and card.bonus is not None and "infiltrated" in card.bonus.types


def infiltrated_clan(player: Player):
    """
    Clan adopté par l'Oculus « Infiltrated » de la main (règle officielle du bonus) : un seul autre clan -> celui-là ;
    deux autres clans -> celui de la carte seule ; trois autres clans ou plus d'un Oculus -> None.
    Les Leaders ne comptent pas comme clan (hypothèse, non documentée).
    """
    oculus = [c for c in player.cards if c.faction == OCULUS]
    if len(oculus) != 1:
        return None
    counts = Counter(c.faction for c in player.cards if c.faction not in (OCULUS, LEADER))
    if len(counts) == 1:
        clan = next(iter(counts))
    elif len(counts) == 2:
        lone = [clan for clan, n in counts.items() if n == 1]
        clan = lone[0] if len(lone) == 1 else None
    else:
        clan = None
    allowed = infiltrable_clans(oculus[0])
    return clan if clan is not None and (allowed is None or clan in allowed) else None


def infiltrable_clans(card: Card):
    """Clans listés sur la carte Oculus (icônes de l'ability, condition « infiltrated:Clan|Clan ») ; None si inconnus."""
    if card.ability is None:
        return None
    for condition in card.ability.effect_conditions:
        if condition.startswith("infiltrated:"):
            return condition[len("infiltrated:"):].split("|")
    return None


def clan_for_bonus(player: Player, card: Card):
    """Clan dont la carte porte le bonus : son propre clan, ou le clan adopté pour un Oculus infiltré."""
    return infiltrated_clan(player) if is_infiltrated(card) else card.faction


def apply_infiltrated_bonus(player: Player, card: Card) -> None:
    """Remplace le bonus de combat d'un Oculus infiltré par celui du clan adopté (None s'il n'y en a pas)."""
    if not is_infiltrated(card):
        return
    clan = infiltrated_clan(player)
    source = next((c for c in player.cards if c.faction == clan and c.bonus is not None), None)
    card.bonus_fight = copy.deepcopy(source.bonus) if source else None


def is_clan_bonus_active(player: Player, card: Card) -> bool:
    """Règle Urban Rivals : le bonus de clan s'active si la main (les 4 cartes) compte au moins 2 cartes du clan."""
    clan = clan_for_bonus(player, card)
    if clan is None:
        return False
    return sum(1 for c in player.cards if clan_for_bonus(player, c) == clan) >= MIN_CLAN_CARDS_FOR_BONUS


def init_fight_data(card: Card, nb_pillz: int, fury: bool):
    card.power_fight = card.power
    card.damage_fight = card.damage
    card.ability_fight = copy.deepcopy(card.ability)
    card.bonus_fight = copy.deepcopy(card.bonus)
    card.leader_fight = None
    if card.ability_fight is not None:
        card.ability_fight.label = f"pouvoir « {card.ability_description} »"
    if card.bonus_fight is not None:
        card.bonus_fight.label = f"bonus « {card.bonus_description} »"
    card.pillz_fight = nb_pillz
    card.fury = fury
    card.attack = 0
    card.cancelled_modifs = set()



def check_round_correct(game: Game, round_data: ProcessRoundInput):
    if round_data.player1_card_index >= 4:
        raise ValueError("Player 1: invalid card index.")
    if round_data.player2_card_index >= 4:
        raise ValueError("Player 2: invalid card index.")
    if round_data.player1_pillz + 3 * round_data.player1_fury > game.ally.pillz + 1:
        raise ValueError("Player 1: too many pillz.")
    if round_data.player2_pillz + 3 * round_data.player2_fury > game.enemy.pillz + 1:
        raise ValueError("Player 2: too many pillz.")
    if game.ally.cards[round_data.player1_card_index].played:
        raise ValueError("Player 1: card already played.")
    if game.enemy.cards[round_data.player2_card_index].played:
        raise ValueError("Player 2: card already played.")
    if game.nb_turn > NB_ROUNDS or game.ally.life <= 0 or game.enemy.life <= 0:
        raise ValueError("Game is already finished.")
