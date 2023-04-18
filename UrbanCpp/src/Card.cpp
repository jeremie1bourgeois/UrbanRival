#include "Card.h"

string Card::getName() const {
    return name;
}

string Card::getFaction() const {
    return faction;
}

int Card::getPower() const {
    return power;
}

int Card::getDamage() const {
    return damage;
}

int Card::getStars() const {
    return stars;
}

string Card::getAbility() const {
    return ability;
}

string Card::getBonus() const {
    return bonus;
}

int Card::getPowerFight() const {
    return powerFight;
}

int Card::getDamageFight() const {
    return damageFight;
}

string Card::getAbilityFight() const {
    return abilityFight;
}

string Card::getBonusFight() const {
    return bonusFight;
}

int Card::getPillzFight() const {
    return pillzFight;
}

int Card::getAttack() const {
    return attack;
}

int Card::getPlayed() const {
    return played;
}

void Card::setPowerFight(int power) {
    powerFight = power;
}

void Card::setDamageFight(int damage) {
    damageFight = damage;
}

void Card::setAbilityFight(const string& ability) {
    abilityFight = ability;
}

void Card::setBonusFight(const string& bonus) {
    bonusFight = bonus;
}

void Card::setPillzFight(int pillz) {
    pillzFight = pillz;
}

void Card::setAttack(int attack) {
    this->attack = attack;
}

void Card::setPlayed(int played) {
    this->played = played;
}
