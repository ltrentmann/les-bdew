"""
Author: Amedeo Ceruti
Contact: amedeo.ceruti@tum.de


Main script to process database data to import to demandlib. Crosses 
with german Zensus 2011, Hausumriss dataset of german buildings.
"""
import logging
import os

import pandas as pd

from datamgmt import process_stock, setup_shapefile, typology, utils
from datamgmt.Parameters import Parameters as Params


# path where raw input data of buildings is located
DATAPATH = './data/raw/example_raw_bdew.shp'
ZENSUSPATH = './data/census/2024-08-12_census-processed.csv'
# path to overall age distribution of buildings in the shapefile
MUNICIPALITYAGESPATH = './data/census/2024-08-12_census-sum.csv'
TABULAPATH = './databases/DE_TABULA_buildingtypes.csv'
NONRESPATH = './databases/DE_type-to-IWU.csv'
RUNID = "example"

# STORING
# path where first gdf for values should be stored
ZONEDIR = f'./inputdata/{RUNID}'  # directory for zone shape files
# write and store file paths
cea_init_path = f'{ZONEDIR}/initialized_bdew_data.shp'
zonepath = f'{ZONEDIR}/bdew-orig.shp'

def main(path_data, RUNID):
    """
    Setup cea gdf and shapefile.
    """
    os.makedirs(ZONEDIR, exist_ok=True)

    # init parameters object
    params = Params(census_path=MUNICIPALITYAGESPATH, iwu_path=NONRESPATH)

    # set up the gdf for bdew
    gdf_cea = setup_shapefile.compute_shapefile(
        importpath=path_data,
        exportpath= cea_init_path,
        params_dict=params.cea
        )

    # Update gdf for bdew with building age and type from zensus data
    gdf_residential, gdf_nonres, gdf_surroundings =  process_stock.assign_categories(
        gdf=gdf_cea,
        zensus_path=ZENSUSPATH,
        tabula_path=TABULAPATH,
        nonres_path=NONRESPATH,
        parameters=params.zensus
    )
    # merge residental and nonresidential
    # subsitute this for concat gdf_stock = gdf_residential.append(gdf_nonres)
    gdf_stock = pd.concat([gdf_residential, gdf_nonres], ignore_index=True)

    # filter out areas from parameters file
    gdf_stock, gdf_surroundings = utils.filter_area(gdf_stock, gdf_surroundings, params.zensus['AREA_FILTER'])
    # flatten again
    gdf_stock = utils.flatten_gdf(gdf_stock)

    # save results in shapefiles
    utils.export_to_shp(gdf_stock, zonepath, params.zensus['EPSG'])
    logging.debug("Exported residential gdf to %s", zonepath)


if __name__ == '__main__':

    print(f"Processing file {DATAPATH}")
    main(DATAPATH, RUNID)
