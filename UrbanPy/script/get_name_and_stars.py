import json

# Charger le fichier source
with open("jsonData_officiel.json", "r") as file:
    data = json.load(file)

# Préparer le nouveau dictionnaire
output = {}

# Parcourir les personnages pour extraire leurs étoiles
for character_name, character_data in data.items():
    # Récupérer les clés numériques qui représentent les étoiles
    stars = [int(star) for star in character_data.keys() if star.isdigit()]
    # Ajouter au nouveau dictionnaire
    output[character_name] = stars

# Sauvegarder dans un nouveau fichier JSON
with open("characters_with_stars.json", "w") as file:
    json.dump(output, file, indent=4)

print("Nouveau fichier JSON généré : characters_with_stars.json")
