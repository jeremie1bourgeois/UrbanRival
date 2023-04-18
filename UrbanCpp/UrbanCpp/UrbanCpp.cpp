
#include <iostream>

class Game {
private:
    Player ally;
    Player enemy;
    const bool turn;
    char nb_turn;

public:
    Game() {
    }

    bool checkEnd() {
        // fonction pour vérifier si la partie est terminée
        // retourne true si la partie est terminée, false sinon
        // implémenter la logique de vérification de fin de partie
    }

    bool winner() {
        // fonction pour déterminer le gagnant de la partie
        // retourne true si le joueur allié a gagné, false sinon
        // implémenter la logique pour déterminer le gagnant
    }

    void Play() {
        // fonction pour jouer un tour de la partie
        // implémenter la logique pour jouer un tour
    }
};
