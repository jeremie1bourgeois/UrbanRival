#include "Game.h"
#include <iostream>

Game::Game() {
    int life = 12;
    int pillz = 12;
    
}

void Game::getCardNames() {
    cout << "Enter the card names for player 1 and his nb stars: " << endl;

    for (int i = 0; i < 4; i++) {
        string cardName;
        cout << "Card " << i + 1 << ": ";
        cin >> cardName;
        searchCardInDB()
    }
}

Card Game::searchCardInDB(string name){
    return;
}


bool Game::checkEnd() {
}

bool Game::winner() {
}

void Game::Play() {
}

// Définition des getters
Player Game::getAlly() const {
    return ally;
}

Player Game::getEnemy() const {
    return enemy;
}

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