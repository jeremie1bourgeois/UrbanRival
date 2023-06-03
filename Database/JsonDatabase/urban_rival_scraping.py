import requests
from bs4 import BeautifulSoup, Tag
import time
import sqlite3
import os
import json
list_ID = [38,31,46,53,25,40,47,32,52,51,48,43,26,54,27,36,3,37,57,56,55,42,4,50,41,49,29,30,33,44,10,28,45]
url = "https://iclintz.com/characters/clan.php?ID="
url_dim = "https://iclintz.com"
# example de nom de faction a récupérer
# <title>iClintz | Aamir - All Stars</title>


class Card:
    def __init__(self):
        self.name = None
        self.faction = None

        self.power = None
        self.damage = None

        self.starOn = None
        self.starOff = None
        
        self.ability = None
        self.bonus = None

    def __str__(self):
        return f"Nom de la carte : {self.name}\nFaction de la carte : {self.faction}\nPuissance de la carte : {self.power}\nDégâts de la carte : {self.damage}\nNombre d'étoiles allumées de la carte : {self.starOn}\nNombre d'étoiles éteintes de la carte : {self.starOff}\nCapacité de la carte : {self.ability}\nBonus de la carte : {self.bonus}"


def recup():
    
    list_all_cards_by_faction = []
    list_all_cards = []
    cpt = 1
    for ID in list_ID:

        list_cards_faction = []
        url_faction = url + str(ID)

        res = requests.get(url_faction)
        soup = BeautifulSoup(res.text, "html.parser") # ,from_encoding='utf-8'

        cards_in_faction = soup.find_all('div', {'class': 'cardFrame'})

        for card_in_menu in cards_in_faction:

            href = card_in_menu.find('a').get('href')

            card = config_card(url_dim + href)

            list_cards_faction += card
            list_all_cards += card
            print(cpt)
            print(card[len(card)-1].name)
            cpt += 1
        
        list_all_cards_by_faction.append(list_cards_faction)
    return list_all_cards


def config_card(url_card):
    res = requests.get(url_card)
    soup = BeautifulSoup(res.text, "html.parser")
    cards_find_level = soup.find_all('div', {'class': 'cardFrame'})

    faction_name = soup.find('title').text.split("-")[1].strip()
    print(faction_name)
    
    list_cards = []

    for div in cards_find_level:
        card = Card()
        
        card.name = div.find('span', {'class': 'cardName'}).text

        card.faction = faction_name

        card.power = div.find('div', {'class': 'cardPH'}).text

        card.damage = div.find('div', {'class': 'cardPDD'}).text
        
        nb_starOn = len(div.find_all('div', {'class': 'cardStarOn'}))
        nb_starOff = len(div.find_all('div', {'class': 'cardStarOff'}))

        card.starOn = nb_starOn
        card.starOff = nb_starOn + nb_starOff

        card.ability = div.find('div', {'class': 'cardPower'}).find('div', {'class': 'vcenterContent'}).text.strip() # .strip() suppr les espaces deb/fin

        card.bonus = div.find('div', {'class': 'cardBonus'}).find('div', {'class': 'vcenterContent'}).text.strip()
        list_cards.append(card)
    return list_cards

def create_database(list_all_cards):
    # Connexion à la base de données SQLite
    conn = sqlite3.connect('dataBase_UrbanRival.db')

    # Suppression de la table 'cartes' s'il existe déjà
    conn.execute("DROP TABLE IF EXISTS cartes")

    # Création de la table 'cartes' dans la base de données avec les colonnes 'name', 'faction', 'power', 'damage', 'starOn', 'starOff', 'ability' et 'bonus'
    conn.execute('''CREATE TABLE IF NOT EXISTS cartes
                     (name TEXT,
                      faction TEXT,
                      power INTEGER,
                      damage INTEGER,
                      starOn INTEGER,
                      starOff INTEGER,
                      ability TEXT,
                      bonus TEXT);''')

    # Insertion des informations de chaque carte dans la table 'cartes'
    for card in list_all_cards:
        conn.execute("INSERT INTO cartes (name, faction, power, damage, starOn, starOff, ability, bonus) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                     (card.name, card.faction, card.power, card.damage, card.starOn, card.starOff, card.ability, card.bonus))
    
    # Enregistrement des changements dans la base de données
    conn.commit()

    # Fermeture de la connexion à la base de données
    conn.close()
    
    print("Base de données créée et remplie avec succès !")


def create_json(list_all_cards, filename):
    # Création d'un dictionnaire pour stocker les informations des cartes
    cards_data = {}

    # Ajout des informations de chaque carte au dictionnaire
    for card in list_all_cards:
        # Vérification si la clé du nom de la carte existe déjà dans le dictionnaire
        if card.name in cards_data:
            # Récupération du dictionnaire existant pour le nom de la carte
            card_dict = cards_data[card.name]
        else:
            # Création d'un nouveau dictionnaire pour le nom de la carte avec les informations initiales
            card_dict = {
                'faction': card.faction,
                'starOff': card.starOff,
                'bonus': card.bonus
            }
            # Ajout du dictionnaire au dictionnaire principal
            cards_data[card.name] = card_dict

        # Ajout des informations de la carte sous la clé card.starOn
        card_dict[card.starOn] = {
            'power': card.power,
            'damage': card.damage,
            'ability': card.ability
        }

    # Écriture du dictionnaire dans le fichier JSON
    with open(filename, 'w') as json_file:
        json.dump(cards_data, json_file, indent=4)

    print("Fichier JSON créé avec succès !")
