class Player {
private:
    Card cardList[5];   // liste d'objets Carte
    int life;           // points de vie
    int pillz;          // points de pillz
    list<tuple<void*, int, int>> effectList;   // liste d'effets

public:
    Player(Card cardList[5], int life, int pillz) : life(life), pillz(pillz) {
        // constructeur pour initialiser les attributs cardList, life et pillz
        for(int i = 0; i < 5; i++) {
            this->cardList[i] = cardList[i];
        }
    }

    // getters et setters pour les attributs
    Card* getCardList() {
        return cardList;
    }

    void setCardList(Card cardList[5]) {
        for(int i = 0; i < 5; i++) {
            this->cardList[i] = cardList[i];
        }
    }

    int getLife() {
        return life;
    }

    void setLife(int life) {
        this->life = life;
    }

    int getPillz() {
        return pillz;
    }

    void setPillz(int pillz) {
        this->pillz = pillz;
    }

    list<tuple<void*, int, int>> getEffectList() {
        return effectList;
    }

    void setEffectList(list<tuple<void*, int, int>> effectList) {
        this->effectList = effectList;
    }

    // méthode pour ajouter un effet à la liste d'effets
    void addEffect(void* effect, int duration, int value) {
        effectList.push_back(make_tuple(effect, duration, value));
    }
};
