# Created by Eric (Jun 2021)
# and is a combination of two scripts originally created by Kevin

import sys
import pandas as pd
import geopandas as gpd
from collections import OrderedDict
from copy import deepcopy
import json
import os

if (len(sys.argv) < 2):
    print("\033[33mgenerateScenario -- Usage")
    print(" \033[36m$ python3 generateScenario <area> <progress=Y>\033[33m")
    print(" where \033[3m<area>\033[0;33m is either \033[1mOttawa\033[0;33m OR \033[1mOntario\033[0;33m")
    print(" and \033[3m<progress=Y>\033[0;33m is a toggle for the progress updates (it defaults to on and a 'N' turns them off\033[0m")
    sys.exit(-1)
#if

no_progress = len(sys.argv) > 2 and sys.argv[2] == "-np"

# Setup variables that handle the area
input_dir          = str(sys.argv[1])
input_area         = json.loads( open(input_dir + "/default.json", "r").read() )["default"]["area"]
cadmium_dir        = "../../cadmium_gis/"
cadmium_dir       += input_area + "/"
area_specific_data = json.loads( open(cadmium_dir + "generatorData.json", "r").read() )
area_id            = area_specific_data["area_id"]
population         = area_specific_data["population_column_name"]
area_col           = area_specific_data["area_col"]
progress_freq      = area_specific_data["progress_freq"]
area_id_clean_csv  = area_id.upper()
adj_csv            = input_area + "_" + area_id.lower() + "_adjacency.csv"
clean_csv          = input_area + "_" + area_id.lower() + "_clean.csv"
gpkg_file          = input_area + "_" + area_id.lower() + ".gpkg"

progress = 0

def shared_boundaries(gdf, id1, id2):
    g1 = gdf[gdf[area_id] == str(id1)].geometry.iloc[0]
    g2 = gdf[gdf[area_id] == str(id2)].geometry.iloc[0]
    return g1.length, g2.length, g1.boundary.intersection(g2.boundary).length
#shared_boundaries()

def get_boundary_length(gdf, id1):
    g1 = gdf[gdf[area_id] == str(id1)].geometry.iloc[0]
    return g1.boundary.length
#get_boundary_length

df     = pd.read_csv(cadmium_dir + clean_csv)   # General information (id, population, area...)
df_adj = pd.read_csv(cadmium_dir + adj_csv)     # Pair of adjacent territories
gdf    = gpd.read_file(cadmium_dir + gpkg_file) # GeoDataFrame with the territories poligons

# Read default state from input json
default_cell  = json.loads( open(input_dir + "/default.json", "r").read()      )
fields        = json.loads( open(input_dir + "/fields.json", "r").read()       )
infectedCells = json.loads( open(input_dir + "/infectedCell.json", "r").read() )

default_state              = default_cell["default"]["state"]
default_vicinity           = default_cell["default"]["neighborhood"]["default_cell_id"]
default_correction_factors = default_vicinity["infection_correction_factors"]
default_correlation        = default_vicinity["correlation"]

nan_rows           = df[ df[population].isnull() ]
zero_pop_rows      = df[ df[population] == 0 ]
invalid_region_ids = list( pd.concat([nan_rows, zero_pop_rows])[area_id_clean_csv] )

adj_full = OrderedDict()
for ind, row, in df_adj.iterrows():
    row_region_id           = row["region_id"]
    row_neighborhood_id     = row["neighbor_id"]
    row_region_id_str       = str(row_region_id)
    row_neighborhood_id_str = str(row_neighborhood_id)

    if row_region_id in invalid_region_ids:
        print("Invalid region ID found:", row_region_id)
        continue
    elif row_neighborhood_id in invalid_region_ids:
        print("Invalid neighborhood region ID found:", row_neighborhood_id)
        continue
    elif row_region_id_str not in adj_full:
        rel_row = df[ df[area_id_clean_csv] == row["region_id"] ].iloc[0, :]
        pop     = int(rel_row[population])
        area    = rel_row[area_col]

        state = deepcopy(default_state)
        state["population"] = pop
        expr = dict()
        expr[row_region_id_str]     = {"state": state, "neighborhood": {}}
        adj_full[row_region_id_str] = expr
    #elif

    l1, l2, shared  = shared_boundaries(gdf, row_region_id, row_neighborhood_id)
    correlation     = (shared/l1 + shared/l2) / 2  # Equation extracted from Zhong paper (boundaries only, we don't have roads info for now)
    if correlation == 0:
        continue

    expr = {"correlation": correlation, "infection_correction_factors": default_correction_factors}
    adj_full[row_region_id_str][row_region_id_str]["neighborhood"][row_neighborhood_id_str]=expr

    if not(no_progress) and ind % progress_freq == 0:
        progress = (int)(70*ind/len(df_adj))
        sys.stdout.write("\r\033[33m" + str(progress) + "%" + "\033[0m")
#for:

for key, value in adj_full.items():
    # Insert every cell into its own neighborhood, a cell is -> cell = adj_full[key][key]
    adj_full[key][key]["neighborhood"][key] = {"correlation": default_correlation, "infection_correction_factors": default_correction_factors}
    if not(no_progress):
        progress = (int)(10 * list(adj_full.keys()).index(key)/len(adj_full.items()))
        sys.stdout.write("\r\033[33m" + str(70 + progress) + "%" + "\033[0m")
#for

# Insert cells from ordered dictionary into index "cells" of a new OrderedDict
template = OrderedDict()
template["cells"] = {}
template["cells"]["default"] = default_cell["default"]

infected_index = list()
for ind, key in enumerate(infectedCells):
    infected_index.append(key)
    if not(no_progress):
        progress = (int)(5 * ind/len(df_adj))
        sys.stdout.write("\r\033[33m" + str(80 + progress) + "%" + "\033[0m")

for key, value in adj_full.items():
    # Write cells in cadmium master format
    template["cells"][key] = value[key]

    # Overwrite the state variables of the infected cell
    # This should be modified to support any number of infected cells contained in the infectedCell.json file
    if key in infected_index:
        template["cells"][key]["state"]["susceptible"] = infectedCells[key]["state"]["susceptible"]
        template["cells"][key]["state"]["exposed"]     = infectedCells[key]["state"]["exposed"]

        if "infected" in infectedCells[key]["state"]:
            template["cells"][key]["state"]["infected"]   = infectedCells[key]["state"]["infected"]
        if "recovered" in infectedCells[key]["state"]:
            template["cells"][key]["state"]["recovered"]  = infectedCells[key]["state"]["recovered"]
        if "fatalities" in infectedCells[key]["state"]:
            template["cells"][key]["state"]["fatalities"] = infectedCells[key]["state"]["fatalities"]
    #if

    if not(no_progress):
        progress = (int)(10 * list(adj_full.keys()).index(key)/len(adj_full.items()))
        sys.stdout.write("\r\033[33m" + str(85 + progress) + "%" + "\033[0m")
#for

# Insert fields object at the end of the json for use with the GIS Webviewer V2
template["fields"] = fields["fields"]
adj_full_json = json.dumps(template, indent=4, sort_keys=False)  # Dictionary to string (with indentation=4 for better formatting)

with open("output/scenario_"+input_dir+".json", "w") as f:
    f.write(adj_full_json)
#with

if not(no_progress):
    sys.stdout.write("\r\033[32m100%" + "\033[0m\n")
else:
    print("\033[32mDone.\033[0m")