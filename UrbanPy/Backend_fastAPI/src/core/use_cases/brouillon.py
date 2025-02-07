
# def apply_bonus_stop_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
#     """
#     Applique une le bonus : "Stop Opp. Ability"
#     """
#     # il n'existe pas de bonus "Stop: Opp. bonus"
#     if ability_2.how == "stop" and ability_2.type == "bonus":
#         bonus_1 = None
#         ability_2 = None
#     elif (bonus_2.how == "Protection" and bonus_2.type == "ability") or (bonus_2.how == "stop" and bonus_2.type == "bonus"):
#         if ability_1.type == "stop" and ability_1.type == "bonus":
#             # tous les effets seraient utilisés ou annulés dans une boucle ?
#             if ability_2.type == "stop" and ability_2.type == "bonus":
#                 ability_1 = None
#                 bonus_1 = None
#                 ability_2 = None
#                 bonus_2 = None
#             # tous les effets seraient utilisés ou annulés ?
#             else:
#                 ability_1 = None
#                 bonus_1 = None
#                 ability_2 = None
#                 bonus_2 = None
#         else:
#             bonus_1 = None
#             bonus_2 = None
#     else:
#         ability_2 = None
        
# def apply_ability_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
#     """
#     Applique une l'ability : "Stop Opp. Bonus"
#     """
#     if ability_2.how == "stop" and ability_2.type == "ability":
#         ability_1 = None
#         bonus_2 = None
#     elif (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "ability"):
#         if bonus_1.type == "stop" and bonus_1.type == "ability":
#             # tous les effets seraient utilisés ou annulés dans une boucle ?
#             if bonus_2.type == "stop" and bonus_2.type == "ability":
#                 ability_1 = None
#                 bonus_1 = None
#                 ability_2 = None
#                 bonus_2 = None
#             # tous les effets seraient utilisés ou annulés ?
#             else:
#                 ability_1 = None
#                 bonus_1 = None
#                 ability_2 = None
#                 bonus_2 = None
#         else:
#             ability_1 = None
#             ability_2 = None
#     else:
#         bonus_2 = None

# # def apply_bonus_stop_bonus(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
# #     """
# #     Applique une le bonus : "Stop Opp. Bonus"
# #     """
#     # # il n'existe pas de bonus "Stop: Opp. bonus"
#     # if ability_2.how == "stop" and ability_2.type == "bonus":
#     #     bonus_1 = None
#     #     ability_2 = None
#     # elif (ability_2.how == "Protection" and ability_2.type == "bonus") or (ability_2.how == "stop" and ability_2.type == "bonus"):
#     #     if bonus_1.type == "stop" and bonus_1.type == "bonus":
#     #         # tous les effets seraient utilisés ou annulés dans une boucle ?
#     #         if bonus_2.type == "stop" and bonus_2.type == "bonus":
#     #             ability_1 = None
#     #             bonus_1 = None
#     #             ability_2 = None
#     #             bonus_2 = None
#     #         # tous les effets seraient utilisés ou annulés ?
#     #         else:
#     #             ability_1 = None
#     #             bonus_1 = None
#     #             ability_2 = None
#     #             bonus_2 = None
#     #     else:
#     #         bonus_1 = None
#     #         bonus_2 = None
#     # else:
#     #     ability_2 = None
              
# def apply_ability_copy_ability(ability_1: Capacity, ability_2: Capacity, bonus_1: Capacity, bonus_2: Capacity):
#     """
#     Applique l'ability : "Copy Opp. Ability"
#     """
#     if ability_2.how == "stop" and ability_2.type == "ability" or ability_2.how == "copy" and ability_2.type == "ability":
#         ability_1 = None
#         ability_2 = None
#     elif bonus_2.how == "stop" and bonus_2.type == "ability":
#         bonus_2 = None
#         if bonus_1.how == "stop" and bonus_1.type == "bonus":
#             if ability_2.how == "copy" and ability_2.type == "bonus":
#                 ability_1 = ability_2.deepcopy()
#                 ability_2 = None
#             ability_1 = ability_2.deepcopy()
#             ability_2 = None
#             bonus_1 = None
#         else:
#             ability_1 = None
#     elif ability_2.how == "stop" and ability_2.type == "bonus":
#         ability_1 = None
#         ability_2 = None
#         bonus_1 = None
#         if bonus_2.condition_effect == "stop":
#             bonus_2.condition_effect = ""
#         else:
#             bonus_2 = None

#     return ability_1, ability_2, bonus_1, bonus_2




# elif capacity.type == "pillz":
#             if capacity.how == "damage":
#                 player1.pillz = min(capacity.borne, player1.pillz + (capacity.value * card1.damage))
#         elif capacity.type == "life_pillz":
#             if capacity.how == "damage":
#                 player1.life = min(capacity.borne, player1.life + (capacity.value * card1.damage))
#                 player1.pillz = min(capacity.borne, player1.pillz + (capacity.value * card1.damage))


import time

# uno = "tata"

# start = time.time()
# for i in range(10000000):
#     if uno in ["toto", "tutu", "titi"]:
#         pass
# print(time.time() - start)

# liste = ["toto", "tutu", "titi"]
# start = time.time()
# for i in range(10000000):
#     if uno in liste:
#         pass
# print(time.time() - start)

# start = time.time()
# for i in range(10000000):
#     if uno == "toto" or uno == "tutu" or uno == "titi":
#         pass

# print(time.time() - start)


# import time

# # Liste de test
# effect_list = [{"type": ["toxine"]} for _ in range(1000000)]

# # Test avec for i in range(nb)
# start = time.time()
# for i in range(len(effect_list)):
#     effect = effect_list[i]
# print("Temps avec range:", time.time() - start)

# # Test avec enumerate
# start = time.time()
# for i, effect in enumerate(effect_list):
#     pass
# print("Temps avec enumerate:", time.time() - start)

liste = ["ability", "bonus"]
liste2 = ["caca", "pipi"]

start = time.time()
for i in range(1000000):
    if any(x in ["caca", "pipi"] for x in ["ability", "bonus"]):
        pass
print(time.time() - start)

start = time.time()
for i in range(1000000):
    if any(x in liste2 for x in liste):
        pass
print(time.time() - start)

start = time.time()
for i in range(10000000):
    if "ability" in liste2 or "bonus" in liste2:
        pass
print(time.time() - start)