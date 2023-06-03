
import base64
import os
import shutil
import time
import random

from itertools import combinations
import numpy as np
import itertools
from itertools import permutations

class Perso:
    def __init__(self, power, faction=None, proba=None):
        self.power = power
        self.faction = faction
        self.proba = None

    def __str__(self):
        return f"Person(power ='{self.power}', faction ='{self.faction}', proba = '{self.proba}'  )"


def proba_4_bons(compo):
    total = 0
    for comb in combinations(compo, 4):
        non_comb = compo.copy()
        non_comb_product = 1
        for e in comb:
            non_comb.remove(e)
        for num in non_comb:
            non_comb_product *= (1 - num.proba)
            # print("(1 - num.power)")
            # print((1 - num.proba))
        total += comb[0].proba * comb[1].proba * comb[2].proba * comb[3].proba * non_comb_product

    for comb in combinations(compo, 5):
        non_comb = compo.copy()
        non_comb_product = 1
        for e in comb:
            non_comb.remove(e)
        for num in non_comb:
            non_comb_product *= (1 - num.proba)
        total += comb[0].proba * comb[1].proba * comb[2].proba * comb[3].proba * comb[4].proba * non_comb_product

    for comb in combinations(compo, 6):
        non_comb = compo.copy()
        non_comb_product = 1
        for e in comb:
            non_comb.remove(e)
        for num in non_comb:
            non_comb_product *= (1 - num.proba)
        total += comb[0].proba * comb[1].proba * comb[2].proba * comb[3].proba * comb[4].proba * comb[5].proba * non_comb_product

    total += compo[0].proba * compo[1].proba * compo[2].proba * compo[3].proba * compo[4].proba * compo[5].proba * compo[6].proba
    return round(total,3)

# print(proba_4_bons([0.26,0.41,0.45,0.93,0.83,0.11,0.71]))
# print(proba_4_bons([0.50,0.50,0.50,0.50,0.50,0.50,0.50]))

def bonus_violet(compo,no_faction):
    if len([c for i, c in enumerate(compo) if c.faction == "v" and i not in no_faction]) >= 3:
        for i in range (7):
            if compo[i].faction == "v" :
                compo[i].proba += 5
                if i-1 >= 0:
                    compo[i-1] += 5
                if i+1 < 7:
                    compo[i+1] += 5

def bonus_orange(compo, no_faction):
    n = 0
    for i in range (7):
        if compo[i].faction != '' and compo[i].faction == '' and not i in no_faction:
            n += 1
    if n >= 3 :
        for i in range(7):
            if compo[i].faction == "o":
                compo[i].proba += 10


# find_best_compo([], [])

def perm_and_def_proba(liste1, adv):
    list_perm = []
    for perm in permutations(liste1):
        list_perm.append(list(perm))

    # list_perm = list(permutations(liste1))
    # list_perm = [list(perm) for perm in permutations(liste1)]
    res = []
    # cpt = 0
    # for perm in list_perm:
    #     if cpt > 2:
    #         exit(0)
    #     print()
    #     for e in perm:
    #         print(e)
    #     print()
    #     cpt += 1
    # print()
    # print()
    # # exit(0)
    # print(round(max(0, min(100, 220 - 281 + 50))/100,2))
    # for e in adv:
    #     print(e)
    # print("\n\n\n")
    
    perm = list_perm[0]
    for i in range(7):
        perm[i].proba = round(max(0, min(100, perm[i].power - adv[i].power + 50))/100,2)
        print(perm[i].proba)
    perm_bis = perm.copy()
    res.append(perm_bis)
    # print(len(res))
    # print("\nokkkkk\n")
    for e in res[0]:
        print(e)
    print(len(res))
    print("\nokkkkk\n")

    perm = list_perm[1]
    
    for i in range(7):
        perm[i].proba = round(max(0, min(100, perm[i].power - adv[i].power + 50))/100,2)
        # if i == 6:
        #     print(perm[i])
        # print(perm[i].proba)
    for e in res[0]:
        print(e)
    res.append(perm.copy())

    # for perm in list_perm:
    #     new = []
    #     for i in range(7):
    #         perm[i].proba = round(max(0, min(100, perm[i].power - adv[i].power + 50))/100,2)
    #         # print(perm[i].proba)
    #     res.append(perm)
    print("\nazeerty\n")
    for e in res[0]:
        print(e)
    print(len(res))
    print("\nazeerty\n")
    for i in range(2):
        print()
        for e in res[i]:
            print(e)
        print()
    exit(0)
    return res

# permutations_listes([153,61,85,95,14,42,53],
#                     [91,23,85,38,219,115,59])

def add_bonus_power(compo,bonus_power):
    for i in range(7):
        compo[i].proba += bonus_power[i]

def find_best_compo(deck,adv,no_faction,no_switch,bonus_power):
    bonus_orange(adv,no_faction)
    bonus_violet(adv,no_faction)
    perms = perm_and_def_proba(deck, adv)
    
    best_compo = []
    best_proba = 0
    cpt = 0
    for p in perms:
        bonus_orange(p,no_faction)
        bonus_violet(p,no_faction)
        # for e in p:
        #     print(e)
        val = proba_4_bons(p)
        # print(val)
        add_bonus_power(p, bonus_power)
        # print(val)
        # cpt += 1
        # if cpt == 3:
        #     exit(0)
        # print(val)
        if val > best_proba:
            print(val)
            best_proba = val
            best_compo = p
    
    for element in best_compo:
        print(element)
    print(f"sa proba est de  {best_proba}")

    return best_compo

P1 = Perso(239,'')
P2 = Perso(261,'')
P3 = Perso(281,'')
P4 = Perso(212,'')
P5 = Perso(241,'')
P6 = Perso(205,'')
P7 = Perso(220,'')

Padv1 = Perso(205,'')
Padv2 = Perso(229,'')
Padv3 = Perso(272,'')
Padv4 = Perso(272,'')
Padv5 = Perso(237,'')
Padv6 = Perso(261,'')
Padv7 = Perso(281,'')

no_switch = []
no_faction = []

val_power1 = 0
val_power2 = 0
val_power3 = 0
val_power4 = 0
val_power5 = 0
val_power6 = 0
val_power7 = 0

bonus_power = [val_power1,val_power2,val_power3,val_power4,val_power5,val_power6,val_power7]


deck = [P1,P2,P3,P4,P5,P6,P7]
deckadv = [Padv1,Padv2,Padv3,Padv4,Padv5,Padv6,Padv7]

find_best_compo(deck, deckadv, no_faction, no_switch, bonus_power)

# a = [1,2,3,4,5,5]
# b = [5,1,2,5,3,8,8,4,6]

# c = set(b)-set(a)
# print(c)


# for e in deck:
#     e.faction = "ajbjfebz"
# for e in deck:
#     print(e)