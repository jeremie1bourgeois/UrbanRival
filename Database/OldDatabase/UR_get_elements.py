from urban_rival_scraping import *
import sqlite3

def get_table_elements(db_path, table_name):
    # Connexion à la base de données
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Exécution de la requête pour récupérer toutes les colonnes de la table spécifiée, sauf l'ID
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    column_names = [description[0] for description in cur.description]
    if 'id' in column_names:
        rows = [row[1:] for row in rows]

    # Fermeture de la connexion à la base de données
    conn.close()

    # Retour des résultats
    return rows

def sort_ignore_numbers(lst):
    return sorted(lst, key=lambda tup: (''.join(filter(lambda c: c not in ['+', '-', ' ', '.'] and not c.isdigit(), str(tup[-1])))) + str(tup[:-1]))



