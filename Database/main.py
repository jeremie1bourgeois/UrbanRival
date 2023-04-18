from urban_rival_scraping import *
from UR_print import *
from UR_create_db import *
from UR_get_elements import *

db = "dataBase_UrbanRival_officielle.db"
name_table = 'capacities_without_conditions'

print_dataBase("dataBase_UrbanRival_officielle.db","cartes")
# print_dataBase(db, name_table)

L = sort_ignore_numbers(get_table_elements(db, name_table))



for row in L:
    print(*row, sep='\n')

# print_table_elements_with_string(db, name_table, "Opp", "At")
# print_table_elements_with_string(db, name_table, "Opp", "At")



print("\n\n")
print_database_info(db)

