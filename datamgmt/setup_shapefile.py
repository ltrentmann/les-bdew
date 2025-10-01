"""
Author: Amedeo Ceruti
Contact: amedeo.ceruti@tum.de
Date: 2022-09-02

Sets up a script file to import to CEA: mainly adds height_ag, floors_ag and Name columns.

Current assumptions:
Cellar floors and height is a constant.
Standard floor height is constant (change to TABULA category later)
"""

import logging
import warnings

# import pandas as pd
import geopandas as gpd
import numpy as np

from datamgmt.utils import import_shp, export_to_shp


__author__ = "Amedeo Ceruti"
# __copyright__ = "Copyright 2022, TU Munich"
__credits__ = ["Amedeo Ceruti"]
# __license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Amedeo Ceruti"
__email__ = "amedeo.ceruti@tum.de"
__status__ = "Dev"


SHPCOLUMNS = ['GML_ID', 'USE_CALC', 'AREA_CALC', 'VOL_CALC', 'HEIGH_MEAS',
    'HEIGH_CALC', 'CONSTRUCTI', 'CENS_GRID', 'geometry']


def init_gdf(gdf, params):
    """
    Initializes needed columns for CEA to the imported geodataframe.
    """

    gdf.insert(0,'Name','')
    gdf.insert(len(gdf.columns), 'height_ag', 0)
    gdf.insert(len(gdf.columns), 'floors_ag', 0)
    gdf.insert(len(gdf.columns), 'height_bg', params['HEIGHT_CELLAR'])
    gdf.insert(len(gdf.columns), 'floors_bg', params['FLOORS_CELLAR'])
    gdf.insert(len(gdf.columns), 'age_code', '')

    # gdf.head()

    return gdf

def write_values(gdf, params):
    """
    Computes and writes values for new geodataframe columns.
    """
    # iterate over rows and assign name, heights and floors
    for index, row in gdf.iterrows():
        # assign name since not all buildings have an GML_ID
        gdf.loc[index, 'Name'] = 'B' + str(index)
        try:
            gdf.loc[index, 'age_code'] = row.CONSTRUCTI
        except AttributeError:
            logging.debug('CONSTRUCTI not in shapefile. Proceeding to insert dummy value')
            # warnings.WarningMessage("CONSTRUCTI not in shapefile. Proceeding to insert dummy value")
            gdf.loc[index, 'age_code'] = "E" #dummy vcalue and print warning
        if ~np.isnan(row.HEIGH_CALC):
            gdf.loc[index,'height_ag'] = row.HEIGH_CALC  # assign height
        else:
            raise ValueError('CALC_H needs to be a real value')

        if ~np.isnan(row.STOREYS):
            gdf.loc[index,'floors_ag'] = int(row.STOREYS)
        else:
            gdf.loc[index,'floors_ag'] = row.HEIGH_CALC//params['HEIGHT_FLOOR']
        # elif np.isnan(row.MEASURED_H) and ~np.isnan(row.HEIGHT_LOD):
        #     gdf.loc[index,'height_ag'] = row.HEIGHT_LOD  # assign height
        #     gdf.loc[index,'floors_ag'] = row.HEIGHT_LOD//params['HEIGHT_FLOOR']

        # force overwriting of height
        if gdf.loc[index, 'floors_ag'] < 1:
            gdf.loc[index, 'floors_ag'] = 1
    # gdf.head()

    if any(gdf['floors_ag'].isna()):
        raise ValueError('Some buildings have nan as floor number. Check input data.')

    return gdf


def compute_shapefile(importpath, exportpath, params_dict):
    """
    Main script to setup the shapefile for CEA with constant height, Name and floor numbers.

    importpath: str. Where the input shapefile is located
    exportpath: str or None. Where the output shapefile should be stored.
    params: cea dictionary (see class Parameters)

    """

    # import shapefile
    gdf = import_shp(importpath, params_dict)
    logging.debug('Imported file from {%s}', importpath)

    # check required shappefile columns  TODO (check if this works)
    if not all([k in gdf.columns.values for k in SHPCOLUMNS]):
        raise ValueError(f"shapefile must must contain attributes {SHPCOLUMNS}")

    # Initialize columns for CEA
    gdf2 = init_gdf(gdf, params_dict)
    logging.debug('geodataframe initialized')

    # Overwrite LoD2-derived values. Assumption: constant height
    gdf3 = write_values(gdf2, params_dict)

    # export
    if exportpath is not None:
        export_to_shp(gdf3, exportpath, params_dict['EPSG'])
        logging.debug('exported shapefile to {%s}',exportpath)
    elif exportpath is None:
        logging.warning('no intermediate CEA shapefile exported')

    return gdf3
