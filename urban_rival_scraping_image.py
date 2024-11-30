import requests
from bs4 import BeautifulSoup
import os

list_ID = [38,31,46,53,25,40,47,32,52,51,48,43,26,54,27,36,3,37,57,56,55,42,4,50,41,49,29,30,33,44,10,28,45]

url = "https://iclintz.com/characters/clan.php?ID="
url_dim = "https://iclintz.com"

def recup():
    
    list_all_cards_by_faction = []
    list_all_cards = []
    i = 0
    for ID in list_ID:

        url_faction = url + str(ID)

        res = requests.get(url_faction)
        soup = BeautifulSoup(res.text, "html.parser")

        cards_in_faction = soup.find_all('div', {'class': 'cardFrame'})

        for card_in_menu in cards_in_faction:

            href = card_in_menu.find('a').get('href')

            config_card(url_dim + href)
            i += 1
    print(i)
    return list_all_cards

def config_card(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.find_all('div', {'class': 'cardFrame'})
    for div in cards:
        name = div.find('span', {'class': 'cardName'}).text
        name = name.replace(' ', '_')
        nb_starOn = len(div.find_all('div', {'class': 'cardStarOn'}))
        name_with_stars = f"{name}_{nb_starOn}"
        imgUrl = div.find('a').get('href')
        download_image(imgUrl, name_with_stars)


def download_image(imgUrl, name_with_stars):
    # Récupère l'image à l'URL imgUrl
    response = requests.get(imgUrl)
    if response.status_code == 200:  # Vérifie si l'image est correctement téléchargée
        # Détermine le chemin d'enregistrement de l'image
        img_path = os.path.join('imageCard', f"{name_with_stars}.jpg")  # Enregistrement au format .jpg ou autre si nécessaire
        
        # Sauvegarde l'image dans le dossier 'imageCard'
        with open(img_path, 'wb') as f:
            f.write(response.content)

recup()