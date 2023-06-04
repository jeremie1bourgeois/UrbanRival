#include "../include/Game.h"
#include <iostream>
#include "../include/Player.h"
#include "annex.cpp"

using namespace std;

Game::Game() {

    string stringNbTurn;
    int intTurn;
    while (true) {
        cout <<  "What turn are we on?" << endl;
        getline(cin, stringNbTurn);
        
        if(! isDigitString(stringNbTurn))
        {
            cout << "\nYour choice should be a number.\n " << endl;
            continue;
        }
        intTurn = stoi(stringNbTurn);
        if(intTurn < 1 || intTurn > 4)
        {
            cout << "\nYour choice is out of range.\n " << endl;
            continue;
        }
        break;
    }
    nb_turn = intTurn;

    string stringTurn;
    while (true) {
        cout << "It's whose turn to play?" << endl;
        cout << "Your turn : 1    ;    his turn : 0" << endl;
        getline(cin, stringTurn);
        
        if(! isDigitString(stringNbTurn) || stringTurn != "1" && stringTurn != "0")
        {
            cout << "\nYour choice should be \"1\" or \"0\".\n " << endl;
            continue;
        }
        break;
    }
    if (stringTurn == "1")
        turn = 1;
    else
        turn = 0;

    ally = new Player("ally");
    enemy = new Player("enemy");
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