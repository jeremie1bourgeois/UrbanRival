#include "Player.h"
#include <iostream>
#include <algorithm>
#include <fstream>
#include <cctype>

class Game {
    
    private:
        Player* ally;
        Player* enemy;
        bool turn;
        char nb_turn;

        void getCardNames();
//        Card* searchCard();

    public:
        Game();
        bool checkEnd();
        bool winner();
        void Play();

        // Getters
        Player getAlly() const;
        Player getEnemy() const;
        bool getTurn() const;
        char getNbTurn() const;

        // Setters
        void setTurn(bool turn);
        void setNbTurn(char nb_turn);
};