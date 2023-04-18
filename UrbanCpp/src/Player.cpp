#include "Player.h"

// getters et setters pour les attributs
array<Card, 4> Player::getCardArray() {
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

