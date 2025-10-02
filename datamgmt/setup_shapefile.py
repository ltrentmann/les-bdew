"""
@author: Lennart Trentmann (lennart.trentmann@tum.de)
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Sets up a shapefile for import to BDEW: adds height_ag, floors_ag, Name, and age_code columns.

Assumptions:
- Cellar floors and height are constant.
- Standard floor height is constant (can be updated to TABULA category later).
"""

import logging
import warnings
import geopandas as gpd
import numpy as np

from datamgmt.utils import import_shp, export_to_shp


SHPCOLUMNS = [
    'GML_ID', 'USE_CALC', 'AREA_CALC', 'VOL_CALC', 'HEIGH_MEAS',
    'HEIGH_CALC', 'CONSTRUCTI', 'CENS_GRID', 'geometry'
]


def init_gdf(gdf, params):
    """
    Initialize columns needed for BDEW in the imported GeoDataFrame.

    Args:
        gdf (GeoDataFrame): Input shapefile as a GeoDataFrame.
        params (dict): Parameter dictionary with constants.

    Returns:
        GeoDataFrame: Updated GeoDataFrame with new columns.
    """
    gdf.insert(0, 'Name', '')
    gdf['height_ag'] = 0
    gdf['floors_ag'] = 0
    gdf['height_bg'] = params['HEIGHT_CELLAR']
    gdf['floors_bg'] = params['FLOORS_CELLAR']
    gdf['age_code'] = ''

    return gdf


def write_values(gdf, params):
    """
    Computes and writes values for new GeoDataFrame columns: Name, height, and floors.

    Args:
        gdf (GeoDataFrame): Initialized GeoDataFrame with new columns.
        params (dict): Parameter dictionary containing HEIGHT_FLOOR.

    Returns:
        GeoDataFrame: Updated GeoDataFrame with computed values.
    """
    for idx, row in gdf.iterrows():
        # Assign unique Name
        gdf.at[idx, 'Name'] = f"B{idx}"

        # Assign age_code from CONSTRUCTI if present, else dummy 'E'
        if hasattr(row, 'CONSTRUCTI'):
            gdf.at[idx, 'age_code'] = row.CONSTRUCTI
        else:
            logging.debug('CONSTRUCTI not in shapefile. Assigning dummy value "E".')
            gdf.at[idx, 'age_code'] = 'E'

        # Assign height_ag
        if not np.isnan(row.HEIGH_CALC):
            gdf.at[idx, 'height_ag'] = row.HEIGH_CALC
        else:
            raise ValueError('HEIGH_CALC must be a numeric value.')

        # Assign floors_ag
        if hasattr(row, 'STOREYS') and not np.isnan(row.STOREYS):
            gdf.at[idx, 'floors_ag'] = int(row.STOREYS)
        else:
            gdf.at[idx, 'floors_ag'] = row.HEIGH_CALC // params['HEIGHT_FLOOR']

        # Ensure minimum 1 floor
        if gdf.at[idx, 'floors_ag'] < 1:
            gdf.at[idx, 'floors_ag'] = 1

    if gdf['floors_ag'].isna().any():
        raise ValueError('Some buildings have NaN as floor number. Check input data.')

    return gdf


def compute_shapefile(importpath, exportpath, params_dict):
    """
    Main script to prepare a shapefile for BDEW with constant height, Name, and floor numbers.

    Args:
        importpath (str): Path to input shapefile.
        exportpath (str or None): Path to export updated shapefile.
        params_dict (dict): Parameter dictionary.

    Returns:
        GeoDataFrame: Updated shapefile GeoDataFrame ready for BDEW.
    """
    # Import shapefile
    gdf = import_shp(importpath, params_dict)
    logging.debug('Imported shapefile from %s', importpath)

    # Check required columns
    if not all(col in gdf.columns for col in SHPCOLUMNS):
        raise ValueError(f"Shapefile must contain attributes: {SHPCOLUMNS}")

    # Initialize columns
    gdf = init_gdf(gdf, params_dict)
    logging.debug('GeoDataFrame initialized with BDEW columns.')

    # Compute column values
    gdf = write_values(gdf, params_dict)

    # Export if path is provided
    if exportpath:
        export_to_shp(gdf, exportpath, params_dict['EPSG'])
        logging.debug('Exported shapefile to %s', exportpath)
    else:
        logging.warning('No export path provided; shapefile not saved.')

    return gdf
