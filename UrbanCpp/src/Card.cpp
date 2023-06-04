#include "../include/Card.h"
#include <iostream>
#include "json.cpp"
#include <fstream>
#include <cctype>
#include <algorithm>
#include "annex.cpp"

using namespace std;

using json = nlohmann::json;

Card::Card() {

    std::cout << "\nWhat's the name of your card? ";
    string cardName;
    std::ifstream file("../../Database/jsonData_officiel.json");
    json data = json::parse(file);
    int cpt;
    vector<string> matchingKeys; // Tableau pour stocker les clés correspondantes
    bool found = false;

    // set the card
    while (!found) {

        getline(cin, cardName);
        matchingKeys.clear(); // Réinitialiser le tableau des clés correspondantes
        cpt = 1;
        
        if (cardName.empty())
        {
            std::cout << "\nWhat's the name of your card? ";
            continue;
        }

        std::cout << '\n';
        for (auto it = data.begin(); it != data.end(); ++it) {

            string keyWithoutMaj = it.key();
            std::transform(keyWithoutMaj.begin(), keyWithoutMaj.end(), keyWithoutMaj.begin(), ::tolower);
            std::transform(cardName.begin(), cardName.end(), cardName.begin(), ::tolower);

            if (keyWithoutMaj.find(cardName) == 0) {
                
                if (keyWithoutMaj == cardName) {
                    std::cout << "Card found: " << it.key() << endl;
                    name = it.key();
                    found = true;
                    break;
                }
                matchingKeys.push_back(it.key()); // Stocker les clés correspondantes
                std::cout << cpt << " : " << it.key() << endl;
                cpt++;
            }
        }

        if (found)
            break;
        
        if (matchingKeys.size() == 0)
        {
            std::cout << "\nSorry, there are no cards starting with that name.\n";
            std::cout << "What's the name of your card again? ";
            continue;
        }

        std::cout << "Please choose your card. If it is not listed, type 'no': ";
        string choice;
        int nbChosen;
        while(getline(cin, choice))
        {
            if (choice == "no")
            {
                std::cout << "\nLet's try again, What's the name of your card? " << endl;
                break;
            }
            if(! isDigitString(choice))
            {
                std::cout << "\nYour chois should be a number, pls choose your card number again : " << endl;
                continue;
            }

            nbChosen = stoi(choice) - 1;
            if (nbChosen >= 0 && nbChosen < matchingKeys.size()) {
                std::cout << "Card found: " << matchingKeys[nbChosen] << endl;
                name = matchingKeys[nbChosen];
                found = true;
                break;
            }
            else {
                std::cout << "\nYour choice is out of range, pls choose your card number again : " << endl;
                continue;
            }
        }
        if (found)
            break;
        
    }
    auto Key = data.find(name);
    faction = (*Key)["faction"];
    bonus = (*Key)["bonus"];
    

    // set the nb of stars or the card
    string res;
    while (true) {
        std::cout << "\nHow many stars have your card : " << endl;
        getline(cin, res);
        if(! isDigitString(res))
        {
            std::cout << "\nYour chois should be a number.\n " << endl;
            continue;
        }
        if(!(*Key).count(res))
        {
            std::cout << "\nThis number of stars doesn't exist.\n " << endl;
            continue;
        }
        stars = stoi(res);
        break;
    }

    auto nbStars = (*Key)[res];
    // set the remaining information of the card
    std::string powerString = nbStars["power"];
    std::string damageString = nbStars["damage"];

    power = stoi(powerString);
    damage = stoi(damageString);
    ability = (nbStars)["ability"];
}

string Card::getName(){
    return name;
}

string Card::getFaction(){
    return faction;
}

int Card::getPower(){
    return power;
}

int Card::getDamage(){
    return damage;
}

int Card::getStars(){
    return stars;
}

string Card::getAbility(){
    return ability;
}

string Card::getBonus(){
    return bonus;
}

int Card::getPowerFight(){
    return powerFight;
}

int Card::getDamageFight(){
    return damageFight;
}

string Card::getAbilityFight(){
    return abilityFight;
}

string Card::getBonusFight(){
    return bonusFight;
}

int Card::getPillzFight(){
    return pillzFight;
}

int Card::getAttack(){
    return attack;
}

int Card::getPlayed(){
    return played;
}



void Card::setPowerFight(int power) {
    powerFight = power;
}

void Card::setDamageFight(int damage) {
    damageFight = damage;
}

void Card::setAbilityFight(string& ability) {
    abilityFight = ability;
}

void Card::setBonusFight(string& bonus) {
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


// int main() {
//     // std::cout << "zerazr" << std::endl;
//     // Game game;
//     // std::cout << game.getNbTurn() << endl;

//     Card c = Card();
//     // std::cout << "Le nom de l'objet est : " << c.getName()<< std::endl;
//     // std::cout << "son pouvoir est : " << c.getAbility()<< std::endl;
//     // std::cout << "sa faction est : " << c.getFaction()<< std::endl;
//     // std::cout << "son bonus est : " << c.getBonus()<< std::endl;
//     // std::cout << "ses dégats sont : " << c.getDamage()<< std::endl;
//     // std::cout << "sa puissance est de : " << c.getPower()<< std::endl;
//     return 0;
// }