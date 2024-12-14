import json

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

# Exemple d'utilisation
file_path = "all_capacities.txt"  # Remplacez par le chemin de votre fichier txt
output_path = "all_capacities.json"      # Chemin du fichier JSON généré
txt_to_json(file_path, output_path)
