# -*- coding: utf-8 -*-
"""
@author: Lennart Trentmann (lennart.trentmann@tum.de); 
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Main script to process building database data for demandlib. 
Crosses with German Zensus 2011 and surroundings dataset of German buildings.
"""

import logging
import os
import pandas as pd

from datamgmt import process_stock, setup_shapefile, typology, utils
from datamgmt.parameters import Parameters as Params


# -----------------------------
# Paths and constants
# -----------------------------
DATAPATH = './data/raw/example_raw_bdew.shp'
ZENSUSPATH = './data/census/2024-08-12_census-processed.csv'
MUNICIPALITYAGESPATH = './data/census/2024-08-12_census-sum.csv'
TABULAPATH = './databases/DE_TABULA_buildingtypes.csv'
NONRESPATH = './databases/DE_type-to-IWU.csv'

RUNID = "example"
ZONEDIR = os.path.join('./inputdata', RUNID)
BDEW_INIT_PATH = os.path.join(ZONEDIR, 'initialized_bdew_data.shp')
ZONEPATH = os.path.join(ZONEDIR, 'bdew-orig.shp')


# -----------------------------
# Main processing function
# -----------------------------
def main(path_data, runid):
    """
    Setup BDEW GeoDataFrame and export shapefiles.

    Parameters
    ----------
    path_data : str
        Path to raw input shapefile of buildings.
    runid : str
        Unique identifier for this run (used for output folders).
    """

    # Ensure output directories exist
    os.makedirs(ZONEDIR, exist_ok=True)

    # Initialize parameters
    params = Params()

    # Compute initial BDEW shapefile
    gdf_bdew = setup_shapefile.compute_shapefile(
        importpath=path_data,
        exportpath=BDEW_INIT_PATH,
        params_dict=params.bdew
    )

    # Assign building categories based on census and typology
    gdf_residential, gdf_nonres, gdf_surroundings = process_stock.assign_categories(
        gdf=gdf_bdew,
        zensus_path=ZENSUSPATH,
        tabula_path=TABULAPATH,
        nonres_path=NONRESPATH,
        parameters=params.zensus
    )

    # Merge residential and non-residential buildings
    gdf_stock = pd.concat([gdf_residential, gdf_nonres], ignore_index=True)

    # Apply area filter from parameters
    gdf_stock, gdf_surroundings = utils.filter_area(
        gdf_stock, gdf_surroundings, params.zensus['AREA_FILTER']
    )

    # Flatten GeoDataFrame for consistency
    gdf_stock = utils.flatten_gdf(gdf_stock)

    # Export final shapefile
    utils.export_to_shp(gdf_stock, ZONEPATH, params.zensus['EPSG'])
    logging.debug("Exported residential GeoDataFrame to %s", ZONEPATH)


# -----------------------------
# Script execution
# -----------------------------
if __name__ == '__main__':
    print(f"Processing file {DATAPATH}")
    main(DATAPATH, RUNID)
