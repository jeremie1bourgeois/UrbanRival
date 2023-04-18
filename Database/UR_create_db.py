from urban_rival_scraping import *
from UR_print import *
import sqlite3

def drop_table(db, name_table):
    sqlite3.connect(db).execute(f"DROP TABLE IF EXISTS {name_table}")

def create_table_capacities_without_conditions(db, name_table):
    # Connexion à la base de données
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()

        # Suppression de la table si elle existe déjà
        cur.execute(f"DROP TABLE IF EXISTS {name_table}")

        # Exécution de la requête pour récupérer toutes les lignes de la table cartes
        cur.execute('SELECT * FROM cartes')
        rows = cur.fetchall()

        # Initialisation d'un ensemble vide pour stocker les résultats uniques
        capacities = set()

        # Boucle sur toutes les lignes de la table cartes
        for row in rows:
            # Si l'élément en sixième position contient un ":", on garde la partie à droite de ce caractère
            if ":" in row[6]:
                capacity = row[6].split(":")[1]
            else:
                capacity = row[6]
            # On retire les espaces aux extrémités de la chaîne de caractères
            capacity = capacity.strip()
            # On ajoute la capacité à l'ensemble des résultats
            capacities.add(capacity)

            # Si l'élément en septième position contient un ":", on garde la partie à droite de ce caractère
            if ":" in row[7]:
                capacity = row[7].split(":")[1]
            else:
                capacity = row[7]
            # On retire les espaces aux extrémités de la chaîne de caractères
            capacity = capacity.strip()
            # On ajoute la capacité à l'ensemble des résultats
            capacities.add(capacity)

        # Tri des capacités dans l'ordre alphabétique
        sorted_capacities = sorted(capacities)

        # Création d'une nouvelle table "capacities" dans la base de données
        cur.execute(f"CREATE TABLE IF NOT EXISTS {name_table} \
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, \
                      capacity TEXT NOT NULL)")

        # Insertion des capacités triées dans la table "capacities"
        cur.executemany(f"INSERT INTO {name_table} (capacity) VALUES (?)",
                        [(c,) for c in sorted_capacities])

        # Affichage du nombre total de capacités
        print(f"Il y a {len(capacities)} abilities et bonuses differents.")

    # Fermeture de la connexion à la base de données
    conn.close()


def create_table_capacities(db, name_table):
    # Connexion à la base de données
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()

        # Suppression de la table s'il elle existe déjà
        cur.execute(f"DROP TABLE IF EXISTS {name_table}")

        # Exécution de la requête pour récupérer toutes les lignes de la table cartes
        cur.execute('SELECT ability, power FROM cartes')
        rows = cur.fetchall()

        # Initialisation d'un ensemble vide pour stocker les résultats uniques
        capacities = set()

        # Boucle sur toutes les lignes de la table cartes
        for row in rows:
            # Ajout de l'élément en sixième position (l'ability) à l'ensemble des résultats
            if row[0] != "":
                capacities.add(str(row[0]))

            # Ajout de l'élément en troisième position (le power) à l'ensemble des résultats
            if row[1] != "":
                capacities.add(str(row[1]))

        # Tri des éléments dans l'ordre alphabétique
        sorted_capacities = sorted(capacities)

        # Création d'une nouvelle table dans la base de données
        cur.execute(f"CREATE TABLE IF NOT EXISTS {name_table} \
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, \
                      capacity TEXT NOT NULL)")

        # Insertion des capacités triées dans la table
        cur.executemany(f"INSERT INTO {name_table} (capacity) VALUES (?)",
                        [(c,) for c in sorted_capacities])

        # Affichage du nombre total d'éléments
        print(f"Il y a {len(capacities)} abilities et powers différents.")

    # Fermeture de la connexion à la base de données
    conn.close()

def create_table_bonus(db_file, table_name):
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        # Suppression de la table si elle existe déjà
        cur.execute(f"DROP TABLE IF EXISTS {name_table}")
        
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, bonus TEXT NOT NULL)")
        cur.execute("SELECT bonus FROM cartes")
        bonus_set = set(bonus[0] for bonus in cur.fetchall())
        cur.executemany(f"INSERT INTO {table_name} (bonus) VALUES (?)", [(bonus,) for bonus in sorted(bonus_set)])
        conn.commit()
        print(f"Il y a {len(bonus_set)} bonus différents.")

