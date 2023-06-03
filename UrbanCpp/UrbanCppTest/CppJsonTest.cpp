#include <iostream>
#include <fstream>
#include "json.cpp"

void printFirstElement(const std::string& filename) {
    // Ouvrir le fichier JSON
    std::ifstream json_file(filename);

    if (json_file.is_open()) {
        // Lire le contenu du fichier JSON dans une chaîne
        std::string json_str((std::istreambuf_iterator<char>(json_file)),
                             std::istreambuf_iterator<char>());

        // Parser la chaîne JSON
        nlohmann::json root = nlohmann::json::parse(json_str);

        // Vérifier si le fichier JSON contient au moins un élément
        if (root.is_array() && !root.empty()) {
            const nlohmann::json& firstElement = root[0];
            std::cout << "Premier élément du fichier JSON :" << std::endl;
            std::cout << firstElement << std::endl;
        } else {
            std::cout << "Le fichier JSON est vide ou ne contient pas d'éléments." << std::endl;
        }

        // Fermer le fichier JSON
        json_file.close();
    } else {
        std::cout << "Impossible d'ouvrir le fichier JSON." << std::endl;
    }
}



