#include <list>
#include <array>
#include "Card.h"

using namespace std;

class Player {


    private:
        array<Card, 4> cardArray;   // liste d'objets Carte
        int life;           // points de vie
        int pillz;          // points de pillz
        list<tuple<void*, int, int>> effectsList;   // liste d'effets

    public:
        Player::Player(const array<Card, 4>& cardArray, int life, int pillz)
            : cardArray(cardArray), life(life), pillz(pillz) {}

        array<Card, 4> getCardArray();
        int getLife();
        int getPillz();
        list<tuple<void*, int, int>> getEffectList();

        void setLife(int life);
        void setPillz(int pillz);
        void setEffectsList(tuple<void*, int, int> effect);

};