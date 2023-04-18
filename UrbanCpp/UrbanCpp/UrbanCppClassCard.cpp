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
    Card(string name, string faction, int power, int damage, int stars, string ability, string bonus,
        int powerFight, int damageFight, string abilityFight, string bonusFight, int pillzFight,
        int attack, int played) : name(name), faction(faction), power(power), damage(damage),
        stars(stars), ability(ability), bonus(bonus), powerFight(powerFight), damageFight(damageFight),
        abilityFight(abilityFight), bonusFight(bonusFight), pillzFight(pillzFight), attack(attack), played(played) {}

    // getters et setters pour les attributs
    string getName() {
        return name;
    }

    void setName(string name) {
        this->name = name;
    }

    string getFaction() {
        return faction;
    }

    void setFaction(string faction) {
        this->faction = faction;
    }

    int getPower() {
        return power;
    }

    void setPower(int power) {
        this->power = power;
    }

    int getDamage() {
        return damage;
    }

    void setDamage(int damage) {
        this->damage = damage;
    }

    int getStars() {
        return stars;
    }

    void setStars(int stars) {
        this->stars = stars;
    }

    string getAbility() {
        return ability;
    }

    void setAbility(string ability) {
        this->ability = ability;
    }

    string getBonus() {
        return bonus;
    }

    void setBonus(string bonus) {
        this->bonus = bonus;
    }

    int getPowerFight() {
        return powerFight;
    }

    void setPowerFight(int powerFight) {
        this->powerFight = powerFight;
    }

    int getDamageFight() {
        return damageFight;
    }

    void setDamageFight(int damageFight) {
        this->damageFight = damageFight;
    }

    string getAbilityFight() {
        return abilityFight;
    }

    void setAbilityFight(string abilityFight) {
        this->abilityFight = abilityFight;
    }

    string getBonusFight() {
        return bonusFight;
    }

    void setBonusFight(string bonusFight) {
        this->bonusFight = bonusFight;
    }

    int getPillzFight() {
        return pillzFight;
    }

    void setPillzFight(int pillzFight) {
        this->pillzFight = pillzFight;
    }

    int getAttack() {
        return attack;
    }

    void setAttack(int attack) {
        this->attack = attack;
    }
}