#include <string>

using namespace std;

class Card {

    private:

        string name;        // nom de la carte
        string faction;     // faction de la carte
        int power;          // puissance de la carte
        int damage;         // d�g�ts de la carte
        int stars;          // �toiles de la carte
        string ability;     // capacit� de la carte
        string bonus;       // bonus de la carte

        int powerFight;     // puissance de combat de la carte
        int damageFight;    // d�g�ts de combat de la carte
        string abilityFight;    // capacit� de combat de la carte
        string bonusFight;  // bonus de combat de la carte
        int pillzFight;     // pillz de combat de la carte
        int attack;         // attaque de la carte
        int played;         // nombre de fois que la carte a �t� jou�e

    public:
        // (string& name, string& faction, int& power, int& damage, int& stars, string& ability, string& bonus)
        //     : name(name), faction(faction), power(power), damage(damage), stars(stars), ability(ability), bonus(bonus),
        //     powerFight(power), damageFight(damage), abilityFight(ability), bonusFight(bonus), pillzFight(0), attack(0), played(0) 
        
        Card();
        
        // Getters
        string getName();
        string getFaction();
        int getPower();
        int getDamage();
        int getStars();
        string getAbility();
        string getBonus();

        int getPowerFight();
        int getDamageFight();
        string getAbilityFight();
        string getBonusFight();
        int getPillzFight();
        int getAttack();
        int getPlayed();

        // Setters

        void setAttack(int attack);
        void setPlayed(int played);

        void setPowerFight(int power);
        void setDamageFight(int damage);
        void setAbilityFight(string& ability);
        void setBonusFight(string& bonus);
        void setPillzFight(int pillz);

};