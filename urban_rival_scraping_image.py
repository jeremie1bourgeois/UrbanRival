import requests
from bs4 import BeautifulSoup
import os

list_ID = [38,31,46,53,25,40,47,32,52,51,48,43,26,54,27,36,3,37,57,56,55,42,4,50,41,49,29,30,33,44,10,28,45]

url = "https://iclintz.com/characters/clan.php?ID="
url_dim = "https://iclintz.com"

def recup():
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

    print(f"✅ {i} cartes trouvées !")

def config_card(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.find_all('div', {'class': 'cardFrame'})
    for div in cards:
        name = div.find('span', {'class': 'cardName'}).text.strip()
        name = name.replace(' ', '_')
        nb_starOn = len(div.find_all('div', {'class': 'cardStarOn'}))
        name_with_stars = f"{name}_{nb_starOn}"
        imgUrl = div.find('a').get('href')

        download_image(imgUrl, name_with_stars)

def download_image(imgUrl, name_with_stars):
    os.makedirs("imageCard", exist_ok=True)  # ✅ Créer le dossier s'il n'existe pas

    response = requests.get(imgUrl)
    if response.status_code == 200:
        img_path = os.path.join('imageCard', f"{name_with_stars}.jpg")
        with open(img_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Image téléchargée : {name_with_stars}")
    else:
        print(f"❌ Erreur téléchargement : {imgUrl}")

recup()
