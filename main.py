"""
Author: Lennart Trentmann
Contact: lennart.trentmann@tum.de
Date: 2023-11-22

Main script to generate ghd heat demand profile based on LOD2 data.
"""
import demandlib.bdew as bdew
import geopandas as gpd
import scripts.demand
import scripts.timeseries_calculation
from scripts.parameters import *

# ignore future warning
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# specifiy input parameters in scripts/parameters.py

if __name__ == "__main__":
    print('============================')
    print('Performing demand caculation...')
    print('============================\n')

    df_shape = gpd.read_file(f'inputdata/{RUNID}/bdew-orig.shp') 
    demand = scripts.demand.demand(
        df_shape,
        spez_heat_bj,
        spez_elec_type,
        bdew_mapping,
        bdew_elec_mapping,
        spez_hot_water_mapping,
        alpha_mapping,
        building_class_mapping,
        RUNID
    )
    demand = scripts.timeseries_calculation.timeseries_calculation(
        demand,
        year,
        RUNID
    )

