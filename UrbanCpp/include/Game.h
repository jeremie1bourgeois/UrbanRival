#include "Player.h"

class Game {
    
    private:
        Player ally;
        Player enemy;
        bool turn;
        char nb_turn;

        void getCardNames();
        Card searchCardInDB();

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