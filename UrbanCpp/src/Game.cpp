#include "../include/Game.h"
#include <iostream>
#include "../../SQLiteCpp-3.2.1/sqlite3/sqlite3.h"

using namespace std;

Game::Game() {
    int life = 12;
    int pillz = 12;
    cout << "HEYHEYHEY" << endl;
}

void Game::getCardNames() {
    cout << "Enter the card names for player 1 and his nb stars: " << endl;

    for (int i = 0; i < 4; i++) {
        string cardName;
        cout << "Card " << i + 1 << ": ";
        cin >> cardName;
        // searchCard()
    }
}


// Card* Game::searchCard(){
//     return nullptr;
// }



// // Définition de la fonction de recherche
// void search_database(const string& db_name, const string& table_name, const string& name_to_find) {
//     try {
//         // Connexion à la base de données
//         SQLite::Database db(db_name);

//         // Exécution d'une requête SQL pour chercher le nom dans la première colonne de la table
//         SQLite::Statement query(db, "SELECT * FROM " + table_name + " WHERE name = ?");
//         query.bind(1, name_to_find);
//         if (query.executeStep()) {
//             // Si le nom est trouvé, récupérer toutes les colonnes de la ligne correspondante
//             string column1 = query.getColumn(0).getString();
//             string column2 = query.getColumn(1).getString();
//             int column3 = query.getColumn(2).getInt();
//             int column4 = query.getColumn(3).getInt();
//             int column5 = query.getColumn(4).getInt();
//             string column6 = query.getColumn(5).getString();
//             string column7 = query.getColumn(6).getString();
//             cout << "Name: " << column1 << ", Column 2: " << column2 << ", Column 3: " << column3
//                  << ", Column 4: " << column4 << ", Column 5: " << column5 << ", Column 6: " << column6
//                  << ", Column 7: " << column7 << endl;
//         } else {
//             // Si le nom n'est pas trouvé, afficher un message d'erreur
//             cout << "Aucun nom trouvé." << endl;
//         }

//         // Fermeture de la connexion
//         db.close();

//     } catch (SQLite::Exception& e) {
//         cerr << "SQLite exception: " << e.what() << endl;
//     }
// }



bool Game::checkEnd() {
    return false;
}

bool Game::winner() {
    return false;
}

void Game::Play() {
}

// Définition des getters
// Player Game::getAlly() const {
//     return ally;
// }

// Player Game::getEnemy() const {
//     return enemy;
// }

bool Game::getTurn() const {
    return turn;
}

char Game::getNbTurn() const {
    return nb_turn;
}

void Game::setTurn(bool turn) {
    this->turn = turn;
}

void Game::setNbTurn(char nb_turn) {
    this->nb_turn = nb_turn;
}