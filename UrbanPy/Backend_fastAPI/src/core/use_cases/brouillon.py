
def apply_bonus_stop_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
    """
    Applique une le bonus : "Stop Opp. Ability"
    """
    # il n'existe pas de bonus "Stop: Opp. bonus"
    if ability_2.how == "stop" and ability_2.type == "bonus":
        bonus_1 = None
        ability_2 = None
    elif (bonus_2.how == "Protection" and bonus_2.type == "ability") or (bonus_2.how == "stop" and bonus_2.type == "bonus"):
        if ability_1.type == "stop" and ability_1.type == "bonus":
            # tous les effets seraient utilisés ou annulés dans une boucle ?
            if ability_2.type == "stop" and ability_2.type == "bonus":
                ability_1 = None
                bonus_1 = None
                ability_2 = None
                bonus_2 = None
            # tous les effets seraient utilisés ou annulés ?
            else:
                ability_1 = None
                bonus_1 = None
                ability_2 = None
                bonus_2 = None
        else:
            bonus_1 = None
            bonus_2 = None
    else:
        ability_2 = None
        
def apply_ability_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
    """
    Applique une l'ability : "Stop Opp. Bonus"
    """
    if ability_2.how == "stop" and ability_2.type == "ability":
        ability_1 = None
        bonus_2 = None
    elif (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "ability"):
        if bonus_1.type == "stop" and bonus_1.type == "ability":
            # tous les effets seraient utilisés ou annulés dans une boucle ?
            if bonus_2.type == "stop" and bonus_2.type == "ability":
                ability_1 = None
                bonus_1 = None
                ability_2 = None
                bonus_2 = None
            # tous les effets seraient utilisés ou annulés ?
            else:
                ability_1 = None
                bonus_1 = None
                ability_2 = None
                bonus_2 = None
        else:
            ability_1 = None
            ability_2 = None
    else:
        bonus_2 = None

# def apply_bonus_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
#     """
#     Applique une le bonus : "Stop Opp. Bonus"
#     """
    # # il n'existe pas de bonus "Stop: Opp. bonus"
    # if ability_2.how == "stop" and ability_2.type == "bonus":
    #     bonus_1 = None
    #     ability_2 = None
    # elif (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "bonus"):
    #     if bonus_1.type == "stop" and bonus_1.type == "bonus":
    #         # tous les effets seraient utilisés ou annulés dans une boucle ?
    #         if bonus_2.type == "stop" and bonus_2.type == "bonus":
    #             ability_1 = None
    #             bonus_1 = None
    #             ability_2 = None
    #             bonus_2 = None
    #         # tous les effets seraient utilisés ou annulés ?
    #         else:
    #             ability_1 = None
    #             bonus_1 = None
    #             ability_2 = None
    #             bonus_2 = None
    #     else:
    #         bonus_1 = None
    #         bonus_2 = None
    # else:
    #     ability_2 = None
              
def apply_ability_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
    """
    Applique l'ability : "Copy Opp. Ability"
    """
    if ability_2.how == "stop" and ability_2.type == "ability" or ability_2.how == "copy" and ability_2.type == "ability":
        ability_1 = None
        ability_2 = None
    elif bonus_2.how == "stop" and bonus_2.type == "ability":
        bonus_2 = None
        if bonus_1.how == "stop" and bonus_1.type == "bonus":
            if ability_2.how == "copy" and ability_2.type == "bonus":
                ability_1 = ability_2.deepcopy()
                ability_2 = None
            ability_1 = ability_2.deepcopy()
            ability_2 = None
            bonus_1 = None
        else:
            ability_1 = None
    elif ability_2.how == "stop" and ability_2.type == "bonus":
        ability_1 = None
        ability_2 = None
        bonus_1 = None
        if bonus_2.condition_effect == "stop":
            bonus_2.condition_effect = ""
        else:
            bonus_2 = None

    return ability_1, ability_2, bonus_1, bonus_2




elif capacity.type == "pillz":
            if capacity.how == "damage":
                player1.pillz = min(capacity.borne, player1.pillz + (capacity.value * card1.damage))
        elif capacity.type == "life_pillz":
            if capacity.how == "damage":
                player1.life = min(capacity.borne, player1.life + (capacity.value * card1.damage))
                player1.pillz = min(capacity.borne, player1.pillz + (capacity.value * card1.damage))