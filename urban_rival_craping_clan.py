import requests
from bs4 import BeautifulSoup
import os
import re

list_ID = [38,31,46,53,25,40,47,32,52,51,48,43,26,54,27,36,3,37,57,56,55,42,4,50,41,49,29,30,33,44,10,28,45]

url = "https://iclintz.com/characters/clan.php?ID="
url_dim = "https://iclintz.com"

def recup():
    
    list_all_cards_by_faction = []
    list_all_cards = []
    for ID in list_ID:

        url_faction = url + str(ID)

        res = requests.get(url_faction)
        soup = BeautifulSoup(res.text, "html.parser")

        img_tag = soup.find("img", {"alt": "Clan Image"})

        if img_tag and 'src' in img_tag.attrs:
            img_url = img_tag['src']
            match = re.search(r"/clan/([A-Z]+)_", img_url)
            name = match.group(1)
            download_image(img_url, f"{name}")
    return list_all_cards

def download_image(imgUrl, name): 
    response = requests.get(imgUrl)
    if response.status_code == 200:  
        img_path = os.path.join('Clan', f"{name}.jpg") 
        
        with open(img_path, 'wb') as f:
            f.write(response.content)
        print(f"Image téléchargée : {name}")

recup()