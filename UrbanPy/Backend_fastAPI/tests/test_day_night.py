"""
Jour / nuit (REGLES 3.13) : tiré au sort à la création de la partie ; de nuit, les cartes prennent leurs textes
« Night: » (night_ability quand le pouvoir du niveau est marqué « Day: », night_bonus pour GhosTown).

Allié  : Hollow Spyke 4★ P7 D5 (Day: -4 Opp Power, Min 4 / Night: Power +4) + Gunslinger 1★ (GhosTown : bonus actif)
         + Aamir 1★ (All Stars) + Zodiack 1★ (Montana)
         bonus GhosTown : Day: Power And Damage + 1 / Night: -1 Opp Pow. And Damage, Min 1
Ennemi : Hollow Spyke 3★ P6 D4, pouvoir verrouillé, seul GhosTown de sa main (bonus inactif)
         + Aamir 1★ + Zodiack 1★ + Serafina Cr 2★ (Rescue)
"""
from src.core.domain.card import Card
from src.core.domain.game import Game
from src.core.domain.player import Player
from src.core.services.game_service import create_game
from src.core.use_cases.process_round import check_round_correct, process_round
from src.schemas.game_schemas import CardInput, GameSetup, ProcessRoundInput

HOLLOW_SPYKE = 0


def _game(night: bool) -> Game:
    ally = Player("ally", 12, 12, [Card("Hollow Spyke", 4, night=night), Card("Gunslinger", 1, night=night),
                                   Card("Aamir", 1, night=night), Card("Zodiack", 1, night=night)])
    enemy = Player("enemy", 12, 12, [Card("Hollow Spyke", 3, night=night), Card("Aamir", 1, night=night),
                                     Card("Zodiack", 1, night=night), Card("Serafina Cr", 2, night=night)])
    return Game(1, True, ally, enemy, [], night=night)


def _play_hollow_spykes(game: Game):
    round_data = ProcessRoundInput(player1_card_index=HOLLOW_SPYKE, player1_pillz=1, player2_card_index=HOLLOW_SPYKE, player2_pillz=1)
    check_round_correct(game, round_data)
    process_round(game, round_data)
    return game.ally.cards[HOLLOW_SPYKE], game.enemy.cards[HOLLOW_SPYKE]


def test_by_day_the_day_ability_and_day_bonus_apply():
    ally, enemy = _play_hollow_spykes(_game(night=False))

    assert (ally.power_fight, ally.damage_fight) == (7 + 1, 5 + 1)      # bonus Power And Damage +1
    assert (enemy.power_fight, enemy.damage_fight) == (6 - 2, 4)         # -4 Opp Power, Min 4


def test_by_night_the_night_ability_and_night_bonus_apply():
    ally, enemy = _play_hollow_spykes(_game(night=True))

    assert (ally.power_fight, ally.damage_fight) == (7 + 4, 5)           # Night: Power +4, bonus tourné vers l'adversaire
    assert (enemy.power_fight, enemy.damage_fight) == (6 - 1, 4 - 1)     # Night: -1 Opp Pow. And Damage, Min 1


# --- Tirage à la création de la partie ---------------------------------------------------------

DECK = GameSetup(
    player1=[CardInput(card_name="Hollow Spyke", nb_stars=4), CardInput(card_name="Gunslinger", nb_stars=1),
             CardInput(card_name="Aamir", nb_stars=1), CardInput(card_name="Zodiack", nb_stars=1)],
    player2=[CardInput(card_name="Hollow Spyke", nb_stars=3), CardInput(card_name="Aamir", nb_stars=1),
             CardInput(card_name="Zodiack", nb_stars=1), CardInput(card_name="Serafina Cr", nb_stars=2)],
)


def test_night_is_drawn_at_random_when_not_requested(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.core.services.game_service.random.choice", lambda options: True)

    game, _ = create_game(DECK)

    assert game.night is True
    assert game.ally.cards[HOLLOW_SPYKE].ability_description == "Night: Power +4"
    assert game.to_dict()["night"] is True


def test_requested_day_or_night_is_kept(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.core.services.game_service.random.choice", lambda options: True)

    game, _ = create_game(DECK.model_copy(update={"night": False}))

    assert game.night is False
    assert game.ally.cards[HOLLOW_SPYKE].ability_description == "Day: -4 Opp Power, Min 4"


def test_saved_games_without_the_night_field_are_by_day(template_game):
    assert template_game.night is False


def test_crook_cr_by_night_costs_its_player_one_life_and_one_pillz_win_or_lose():
    # Night: Vict. Or Def.: -1 Life & Pillz, Min 0 (de jour : +1 Pillz And Life)
    ally = Player("ally", 12, 12, [Card("Crook Cr", 4, night=True), Card("Aamir", 1, night=True),
                                   Card("Zodiack", 1, night=True), Card("Serafina Cr", 2, night=True)])
    enemy = Player("enemy", 12, 12, [Card("Hollow Spyke", 3, night=True), Card("Aamir", 1, night=True),
                                     Card("Zodiack", 1, night=True), Card("Serafina Cr", 2, night=True)])
    game = Game(1, True, ally, enemy, [], night=True)
    round_data = ProcessRoundInput(player1_card_index=0, player1_pillz=1, player2_card_index=0, player2_pillz=3)
    check_round_correct(game, round_data)

    process_round(game, round_data)   # Crook Cr 8 x 1 < Hollow Spyke 6 x 3 : défaite, 4 dégâts

    assert (game.ally.life, game.ally.pillz) == (12 - 4 - 1, 12 - 1)
