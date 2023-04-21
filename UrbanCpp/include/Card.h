#include <string>

using namespace std;

class Card {

    private:

        const string name;        // nom de la carte
        const string faction;     // faction de la carte
        const int power;          // puissance de la carte
        const int damage;         // d�g�ts de la carte
        const int stars;          // �toiles de la carte
        const string ability;     // capacit� de la carte
        const string bonus;       // bonus de la carte

        int powerFight;     // puissance de combat de la carte
        int damageFight;    // d�g�ts de combat de la carte
        string abilityFight;    // capacit� de combat de la carte
        string bonusFight;  // bonus de combat de la carte
        int pillzFight;     // pillz de combat de la carte
        int attack;         // attaque de la carte
        int played;         // nombre de fois que la carte a �t� jou�e

    public:

        Card(const string& name, const string& faction, const int& power, const int& damage, const int& stars, const string& ability, const string& bonus)
            : name(name), faction(faction), power(power), damage(damage), stars(stars), ability(ability), bonus(bonus),
            powerFight(power), damageFight(damage), abilityFight(ability), bonusFight(bonus), pillzFight(0), attack(0), played(0) {}
        
        // Getters
        string getName() const;
        string getFaction() const;
        int getPower() const;
        int getDamage() const;
        int getStars() const;
        string getAbility() const;
        string getBonus() const;
        int getPowerFight() const;
        int getDamageFight() const;
        string getAbilityFight() const;
        string getBonusFight() const;
        int getPillzFight() const;
        int getAttack() const;
        int getPlayed() const;

        // Setters
        void setPowerFight(int power);
        void setDamageFight(int damage);
        void setAbilityFight(const string& ability);
        void setBonusFight(const string& bonus);
        void setPillzFight(int pillz);
        void setAttack(int attack);
        void setPlayed(int played);
};