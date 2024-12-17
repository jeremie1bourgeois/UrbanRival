import json
import os
import re

# FONCTION: extrait les nom des personnages et leurs étoiles du fichier jsonData_officiel.json et les sauvegarde dans un nouveau fichier
def extract_character_stars(input_file, output_file):
    # Charger le fichier source
    with open(input_file, "r") as file:
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
    with open(output_file, "w") as file:
        json.dump(output, file, indent=4)

    # Rendre le fichier en lecture seule
    os.chmod(output_file, 0o444)

    print(f"Nouveau fichier JSON généré : {output_file}")

# FONCTION: converti le fichier txt avec toutes les capacités copier coller depuis le site officiel en un fichier json
# PROBLEME: il n'y a pas toutes les capacités
def txt_to_json(file_path, output_path):
    data = {
        "capacity": []
    }

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Diviser le fichier en blocs basés sur les lignes vides
    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.split("\n")
        if len(lines) > 1:
            description = lines[0].strip()
            explanation = "\n".join(line.strip() for line in lines[1:])
        else:
            description = lines[0].strip()
            explanation = ""

        data["capacity"].append({
            "description": description,
            "explanation": explanation
        })

    # Écrire le fichier JSON
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    # Rendre le fichier en lecture seule
    os.chmod(output_path, 0o444)

# FONCTION: extrait les capacités du jsonData_officiel.json et les sauvegarde dans un nouveau fichier (bonus et ability sans doublons et sans les abilities vides)
# RETURN: un fichier json avec les capacités dans dans la clé "description"
def extract_capacities(input_file, output_file):
    # Charger le fichier JSON existant
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Créer un ensemble pour stocker les capacités uniques
    unique_capacities = set()

    # Parcourir chaque personnage pour extraire le bonus et l'ability du niveau le plus haut
    for character, details in data.items():
        # Ajouter le bonus si présent
        if 'bonus' in details:
            unique_capacities.add(details['bonus'].strip())
        
        # Trouver le niveau le plus haut
        highest_level = max((int(level) for level in details if level.isdigit()), default=None)
        if highest_level is not None:
            ability = details[str(highest_level)].get('ability', '').strip()
            if ability:
                unique_capacities.add(ability)

    # Créer une liste de dictionnaires avec les capacités uniques
    capacities_list = [{"description": capacity} for capacity in unique_capacities]

    # Construire le nouveau JSON
    output_data = {
        "capacity": capacities_list
    }

    # Sauvegarder dans un nouveau fichier JSON
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(output_data, file, ensure_ascii=False, indent=4)

    # Rendre le fichier en lecture seule
    os.chmod(output_file, 0o444)

    print(f"Les capacités ont été extraites et sauvegardées dans '{output_file}'.")


def extract_and_replace_numbers(input_file, output_file):
    '''Extrait les capacités du fichier JSON, remplace les nombres par X et Y, et sauvegarde dans un nouveau fichier JSON.'''
    # Charger le fichier JSON existant
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Parcourir chaque capacité pour remplacer les nombres
    for capacity in data['capacity']:
        description = capacity['description']

        # Trouver tous les nombres dans la description (y compris les négatifs)
        matches = re.findall(r'-?\d+', description)

        # Créer une version modifiée de la description
        if len(matches) >= 2:  # Assurer qu'on a au moins 2 nombres
            modified_description = description.replace(matches[0], matches[0].replace(matches[0], '-X' if matches[0].startswith('-') else 'X'), 1)
            modified_description = modified_description.replace(matches[1], matches[1].replace(matches[1], '-Y' if matches[1].startswith('-') else 'Y'), 1)
        elif len(matches) == 1:  # Si un seul nombre est trouvé
            modified_description = description.replace(matches[0], '-X' if matches[0].startswith('-') else 'X', 1)
        else:  # Si aucun nombre n'est trouvé
            modified_description = description

        # Ajouter une nouvelle clé avec la description modifiée
        capacity['description_with_var'] = modified_description

    # Sauvegarder dans un nouveau fichier JSON
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    # Rendre le fichier en lecture seule
    os.chmod(output_file, 0o444)

    print(f"Les capacités ont été modifiées et sauvegardées dans '{output_file}'.")

# extract_and_replace_numbers("all_capacities_v2.json", "all_capacities_v3.json")


def group_by_description_with_var(input_file, output_file):
    """
        Lit un fichier JSON contenant des capacités avec leurs descriptions (`description`) et une version modifiée 
        (`description_with_var`). Cette fonction regroupe toutes les descriptions originales qui partagent la même 
        version modifiée (`description_with_var`) dans une structure organisée, en éliminant les doublons.

        Chaque entrée dans le fichier de sortie contient :
        - `description_with_var`: La version modifiée de la description avec des variables (X, Y).
        - `descriptions`: Une liste des descriptions originales associées à cette version modifiée.
    """
    # Charger le fichier JSON existant
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Dictionnaire pour regrouper les descriptions
    grouped = {}

    # Parcourir chaque capacité pour regrouper les descriptions
    for capacity in data['capacity']:
        description = capacity['description']
        description_with_var = capacity['description_with_var']

        # Si la description_with_var n'existe pas encore dans le dictionnaire, l'ajouter
        if description_with_var not in grouped:
            grouped[description_with_var] = {
                "descriptions": []
            }

        # Ajouter la description originale si elle n'est pas déjà dans la liste
        if description not in grouped[description_with_var]["descriptions"]:
            grouped[description_with_var]["descriptions"].append(description)

    # Construire la nouvelle structure des capacités
    grouped_capacity = [
        {
            "description_with_var": key,
            "descriptions": value["descriptions"]
        }
        for key, value in grouped.items()
    ]

    # Sauvegarder dans un nouveau fichier JSON
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump({"capacity": grouped_capacity}, file, ensure_ascii=False, indent=4)
        
    os.chmod(output_file, 0o444)
    print(f"Les descriptions ont été regroupées et sauvegardées dans '{output_file}'.")
    
# group_by_description_with_var("all_capacities_v3.json", "all_capacities_v4.json")