#include "../include/Player.h"
#include <iostream>
#include <algorithm>
#include <fstream>
#include <cctype>
#include "annex.cpp"

Player::Player(string name) {

    // define the player's life
    string stringLife;
    while (true) {
        cout << "how many LIFE have " << name << " : " << endl;
        getline(cin, stringLife);
        
        if(! isDigitString(stringLife))
        {
            std::cout << "\nYour chois should be a number.\n " << endl;
            continue;
        }

        life = stoi(stringLife);
        break;
    }

    // define the player's pillz
    string stringPillz;
    while (true) {
        cout << "how many PILLZ have " << name << " : " << endl;
        getline(cin, stringPillz);
        
        if(! isDigitString(stringPillz))
        {
            std::cout << "\nYour chois should be a number.\n " << endl;
            continue;
        }

        pillz = stoi(stringPillz);
        break;
    }
    for (int i = 0; i < 4; i++) {
        cardArray[i] = new Card();
    }
    
}

Player::~Player() {
    for(int i = 0; i < 4; i++) {
        delete cardArray[i];
    }
}

// getters et setters pour les attributs
array<Card *, 4> Player::getCardArray() {
    return cardArray;
}

int Player::getLife() {
    return life;
}

void Player::setLife(int life) {
    this->life = life;
}

int Player::getPillz() {
    return pillz;
}

void Player::setPillz(int pillz) {
    this->pillz = pillz;
}

list<tuple<void*, int, int>> Player::getEffectList() {
    return effectsList;
}

void Player::setEffectsList(tuple<void*, int, int> effect) {
    this->effectsList.push_back(effect);
}

int main() {
    Player p = Player("moi");
    return 0;
}