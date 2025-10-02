# -*- coding: utf-8 -*-
"""
@author: Lennart Trentmann (lennart.trentmann@tum.de); 
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Generate standard load profiles for heat and electricity in buildings based on LOD2 data 
using the LES-BDEW approach via the demandlib package.
"""

import warnings
import geopandas as gpd
import demandlib.bdew as bdew
import scripts.demand
import scripts.timeseries_calculation

# Suppress future warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# -----------------------------
# Main execution
# -----------------------------
if __name__ == "__main__":
    print("============================")
    print("Performing demand calculation...")
    print("============================\n")

    # Parameters
    RUNID = "example"
    YEAR = 2022  # Year of demand profile

    # Path to processed BDEW building data
    DATAPATH = f'inputdata/{RUNID}/bdew-orig.shp'

    # Load building shapefile
    df_shape = gpd.read_file(DATAPATH)

    # Calculate heat and electricity demand per building
    demand_df = scripts.demand.demand(
        df_shape,
        RUNID
    )

    # Generate hourly timeseries based on BDEW standard load profiles
    demand_timeseries = scripts.timeseries_calculation.timeseries_calculation(
        demand_df,
        YEAR,
        RUNID
    )
