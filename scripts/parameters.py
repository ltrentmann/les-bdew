"""
Author: Lennart Trentmann
Contact: lennart.trentmann@tum.de
Date: 2023-11-22

Main script to generate ghd heat demand profile based on LOD2 data.
"""

import csv

import geopandas as gpd
import pandas as pd

# define input parameters
year = 2022  # year of demand profile
region = ['Garching b.München, St']  # region of demand profile
RUNID = "example" #

# import shapefile with geopandas
df_shape = gpd.read_file(f'inputdata/example/bdew-orig.shp')  

# import parameters

# Deutsche Energie-Agentur GmbH. DENA-GEBÄUDEREPORT 2023
with open('databases/spez_hot_water_mapping.csv', mode='r') as infile:
    reader = csv.reader(infile, delimiter=';')
    spez_hot_water_mapping = {rows[0]: float(rows[1]) for rows in reader}

# VDI 3807 Blatt 1 file:///C:/Users/ga87ces/Downloads/fulltext180189525.pdf
with open('databases/alpha_mapping.csv', mode='r') as infile:
    reader = csv.reader(infile, delimiter=';')
    alpha_mapping = {rows[0]: float(rows[1]) for rows in reader}

# mapping of bdew profiles to BD_FUNCTIO
with open('databases/bdew_mapping.csv', mode='r') as infile:
    reader = csv.reader(infile, delimiter=';')
    bdew_mapping = {rows[0]: rows[1] for rows in reader}

# mapping of bdew elec profiles to BD_FUNCTIO
with open('databases/bdew_elec_mapping.csv', mode='r') as infile:
    reader = csv.reader(infile, delimiter=';')
    bdew_elec_mapping = {rows[0]: rows[1] for rows in reader}

# values from https://github.com/IWUGERMANY/Nichtwohngebaeude-Typologie-Deutschland/tree/main
spez_heat_bj = pd.read_csv('databases/spez_heat_bj.csv', sep=';', encoding="ISO-8859-1", index_col=0)
spez_elec_type = pd.read_csv('databases/spez_elec.csv', sep=';', encoding="ISO-8859-1", index_col=0)
building_class_mapping = pd.read_csv('databases/building_class_mapping.csv', sep=';', encoding="ISO-8859-1", index_col=0)