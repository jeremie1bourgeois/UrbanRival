"""
Rejoue dans le moteur les exemples officiels de l'article 2.8 du support Urban Rivals (résolution des Stops)
et le cas « Bet > 3 Pillz » du bonus Zenith. Voir docs/REGLES.md § 3.1 et § 3.8.

Lancer depuis UrbanPy/Backend_fastAPI :  .venv/bin/python scripts/regles_kb91_check.py
Scénario des tests de niveau 1 : Amelia (allié, P3) contre Asporov (ennemi, P7), 1 pillz chacun.
"""
import json
import sys

sys.path.insert(0, ".")

from src.core.domain.game import Game            # noqa: E402
from tests.conftest import TEMPLATE_PATH          # noqa: E402
from tests.test_apply_capacity_lvl_1 import play  # noqa: E402


def fresh() -> Game:
    with open(TEMPLATE_PATH) as file:
        return Game.from_dict_template(json.load(file))


def main() -> None:
    # Exemple 1 : ability « +8 Attack » + bonus SoB contre bonus SoA. Officiel : le +8 s'applique.
    amelia, _ = play(fresh(), ally_ability="Attack +8", ally_bonus="Stop Opp. Bonus", enemy_bonus="Stop Opp. Ability")
    print(f"KB91 ex.1  attaque Amelia = {amelia.attack:2d}   (officiel : 11)")

    # Exemple 2 : bonus « Power +2 » + ability SoA contre ability SoB. Officiel : le SoA s'applique, le bonus tient.
    amelia, _ = play(fresh(), ally_ability="Stop Opp. Ability", ally_bonus="Power +2", enemy_ability="Stop Opp. Bonus", enemy_bonus=None)
    print(f"KB91 ex.2  power Amelia   = {amelia.power_fight:2d}   (officiel : 5)")

    # Bet > 3 Pillz : « including free Pillz and excluding Fury » -> actif dès 4 pillz au total.
    for pillz in (4, 5):
        game = fresh()
        amelia, _ = play(game, ally_ability="Bet > 3 Pillz: +3 Life", enemy_bonus=None, ally_pillz=pillz)
        print(f"Bet        {pillz} pillz au total : gagné={amelia.win}, vie alliée={game.ally.life}   (officiel : 15 dès 4 pillz)")


if __name__ == "__main__":
    main()
