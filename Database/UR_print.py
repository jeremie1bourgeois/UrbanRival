from urban_rival_scraping import *
import sqlite3

def print_database_info(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer le nom de toutes les tables de la base de données
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()

    # Affichage du nombre total de tables dans la base de données
    print(f"Il y a {len(tables)} tables dans la base de données.")

    # Boucle sur toutes les tables de la base de données
    for table in tables:
        table_name = table[0]

        # Exécution de la requête pour récupérer le nombre d'éléments dans chaque table
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]

        # Affichage du nom de la table et de son nombre d'éléments
        print(f"\nTable '{table_name}':")
        print(f"{count} éléments")

    # Fermeture de la connexion à la base de données
    conn.close()



def print_table_elements_with_string(db, name_table, str1, str2=""):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les lignes de la table spécifiée
    cur.execute(f'SELECT * FROM {name_table}')
    rows = cur.fetchall()

    # Affichage des résultats contenant le string "opp" et "at"
    print(f"Contenu de la table '{name_table}':")
    for row in rows:
        for element in row:
            if isinstance(element, str) and str1 in element and str2 in element:
                print(element)

    # Fermeture de la connexion à la base de données
    conn.close()


def print_dataBase(db, name_table):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les lignes de la table spécifiée
    cur.execute(f'SELECT * FROM {name_table}')
    rows = cur.fetchall()

    # Affichage des résultats
    print(f"Contenu de la table '{name_table}':")
    for row in rows:
        print(*row, sep=", ")

    # Affichage du nombre total d'éléments
    print(f"\nIl y a {len(rows)} éléments dans la table '{name_table}'.")

    # Fermeture de la connexion à la base de données
    conn.close()





def print_all_abilities(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Exécution de la requête pour récupérer toutes les lignes de la table cartes
    cur.execute('SELECT * FROM cartes')
    rows = cur.fetchall()

    # Initialisation d'un dictionnaire vide pour stocker les résultats uniques
    results = {}

    # Boucle sur toutes les lignes de la table cartes
    for row in rows:
        # Vérification si l'élément en septième position est déjà dans le dictionnaire des résultats
        if row[6] not in results:
            # Ajout de l'élément au dictionnaire des résultats avec une valeur de 1
            results[row[6]] = 1
        else:
            # Incrémentation de la valeur associée à l'élément dans le dictionnaire des résultats
            results[row[6]] += 1

    # Tri des éléments dans l'ordre alphabétique
    sorted_results = sorted(results.items())

    # Affichage des résultats
    for result in sorted_results:
        print(f"{result[0]} : {result[1]}")

    # Affichage du nombre de pouvoirs différents
    print(f"\nIl y a {len(results)} pouvoirs differents.")

    # Fermeture de la connexion à la base de données
    conn.close()

def print_all_bonus(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Exécution de la requête pour récupérer toutes les lignes de la table cartes
    cur.execute('SELECT * FROM cartes')
    rows = cur.fetchall()

    # Initialisation d'un dictionnaire vide pour stocker les résultats uniques
    results = {}

    # Boucle sur toutes les lignes de la table cartes
    for row in rows:
        # Vérification si l'élément en septième position est déjà dans le dictionnaire des résultats
        if row[6] not in results:
            # Ajout de l'élément au dictionnaire des résultats avec une valeur de 1
            results[row[7]] = 1
        else:
            # Incrémentation de la valeur associée à l'élément dans le dictionnaire des résultats
            results[row[7]] += 1

    # Tri des éléments dans l'ordre alphabétique
    sorted_results = sorted(results.items())

    # Affichage des résultats
    for result in sorted_results:
        print(f"{result[0]} : {result[1]}")

    # Affichage du nombre de pouvoirs différents
    print(f"\nIl y a {len(results)} pouvoirs différents.")

    # Fermeture de la connexion à la base de données
    conn.close()


def print_max_power(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer le power maximum
    cur.execute('SELECT MAX(power) FROM cartes')
    max_power = cur.fetchone()[0]

    # Exécution de la requête pour récupérer toutes les cartes ayant le power maximum
    cur.execute('SELECT * FROM cartes WHERE power = ?', (max_power,))
    rows = cur.fetchall()

    # Affichage des résultats
    if len(rows) == 1:
        print(f"Il y a 1 carte avec le power maximum ({max_power}):")
    else:
        print(f"Il y a {len(rows)} cartes avec le power maximum ({max_power}):")
    for row in rows:
        print(f"- {row[0]} ({row[1]}) : {row[2]} / {row[3]}")

    # Fermeture de la connexion à la base de données
    conn.close()


def print_all_capacities(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les lignes de la table cartes
    cur.execute('SELECT * FROM cartes')
    rows = cur.fetchall()

    # Initialisation d'un ensemble vide pour stocker les résultats uniques
    results = set()

    # Boucle sur toutes les lignes de la table cartes
    for row in rows:
        # Ajout de l'élément en sixième position (l'ability) à l'ensemble des résultats
        results.add(row[6])
        # Ajout de l'élément en septième position (le bonus) à l'ensemble des résultats
        results.add(row[7])

    # Tri des éléments dans l'ordre alphabétique
    sorted_results = sorted(results)

    # Affichage des résultats
    print("Abilities et Bonuses :")
    for result in sorted_results:
        print(result)

    # Affichage du nombre total d'éléments
    print(f"\nIl y a {len(results)} abilities et bonuses differents.")

    # Fermeture de la connexion à la base de données
    conn.close()



def print_all_capacities_without_conditions(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les lignes de la table cartes
    cur.execute('SELECT * FROM cartes')
    rows = cur.fetchall()

    # Initialisation d'un ensemble vide pour stocker les résultats uniques
    results = set()

    # Boucle sur toutes les lignes de la table cartes
    for row in rows:
        # Si l'élément en sixième position contient un ":", on garde la partie à droite de ce caractère
        if ":" in row[6]:
            result = row[6].split(":")[1]
        else:
            result = row[6]
        # On retire les espaces aux extrémités de la chaîne de caractères
        result = result.strip()
        # On ajoute le résultat à l'ensemble des résultats
        results.add(result)

        # Si l'élément en septième position contient un ":", on garde la partie à droite de ce caractère
        if ":" in row[7]:
            result = row[7].split(":")[1]
        else:
            result = row[7]
        # On retire les espaces aux extrémités de la chaîne de caractères
        result = result.strip()
        # On ajoute le résultat à l'ensemble des résultats
        results.add(result)

    # Tri des éléments dans l'ordre alphabétique
    sorted_results = sorted(results)

    # Affichage des résultats
    print("Abilities et Bonuses :")
    for result in sorted_results:
        print(result)

    # Affichage du nombre total d'éléments
    print(f"\nIl y a {len(results)} abilities et bonuses differents.")

    # Fermeture de la connexion à la base de données
    conn.close()


def print_all_labels(db):
    # Connexion à la base de données
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les lignes de la table cartes
    cur.execute('SELECT * FROM cartes')
    rows = cur.fetchall()

    # Initialisation d'un ensemble vide pour stocker les résultats uniques
    results = set()

    # Boucle sur toutes les lignes de la table cartes
    for row in rows:
        # Si l'élément en sixième position contient un ":", on garde la partie à gauche de ce caractère
        if ":" in row[6]:
            result = row[6].split(":")[0]
        else:
            result = ""
        # On retire les espaces aux extrémités de la chaîne de caractères
        result = result.strip()
        # On ajoute le résultat à l'ensemble des résultats
        results.add(result)

        # Si l'élément en septième position contient un ":", on garde la partie à gauche de ce caractère
        if ":" in row[7]:
            result = row[7].split(":")[0]
        else:
            result = ""
        # On retire les espaces aux extrémités de la chaîne de caractères
        result = result.strip()
        # On ajoute le résultat à l'ensemble des résultats
        results.add(result)

    # Tri des éléments dans l'ordre alphabétique
    sorted_results = sorted(results)

    # Affichage des résultats
    print("Labels :")
    for result in sorted_results:
        print(result)

    # Affichage du nombre total d'éléments
    print(f"\nIl y a {len(results)} labels differents.")

    # Fermeture de la connexion à la base de données
    conn.close()
    print("??")


