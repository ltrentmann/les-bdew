"""
Author: Amedeo Ceruti
Contact: amedeo.ceruti@tum.de
Date: 2022-09-27


"""

import os
import logging
import warnings

import pandas as pd
import shapely.geometry
import geopandas as gpd
# import numpy as np

__author__ = "Amedeo Ceruti"
# __copyright__ = "Copyright 2022, TU Munich"
__credits__ = ["Amedeo Ceruti"]
# __license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Amedeo Ceruti"
__email__ = "amedeo.ceruti@tum.de"
__status__ = "Dev"


def import_shp(path, params):
    """
    Read preprocessed (in psql) shapefile (HU, LoD2) data and store in gpd.dataframe.


    :param locator: An InputLocator to locate input files
    :type locator: cea.inputlocator.InputLocator

    :returns: geopandas.DataFrame

    """

    # Read preprocessed shapefile (HU, LoD2) data and store in gpd.dataframe
    gdf = gpd.read_file(path)
    # print(gdf.crs)
    if gdf.crs is None:
        gdf.crs = 'epsg:25832'
        warnings.warn(f'No crs found in {path}. Set to {gdf.crs}')
    gdf.to_crs(epsg=params['EPSG'], inplace=True)
    # print(len(gdf))
    # gdf.head()
    return gdf


def import_csv(path, sep = ",", fillna=0, index_col=None):
    """
    Read preprocessed zensus data csv and store in pd.dataframe.

    inputs
    path: string with csv file location
    sep: string with separator of csv file. Default: ","
    fillna: None or float. with what to replace NaN values in csv file.
        Default = 0. 

    returns:
    df: pandas.DataFrame.
    """

    df = pd.read_csv(path, sep=sep, engine='python', index_col=index_col)
    # replace nan by 0
    if fillna is not None:
        df = df.fillna(fillna)
    # dfzensus.head()

    return df


def export_to_shp(gdf, path, epsg):
    """
    Export a geodataframe to a shape file.
    """
    gdf.to_crs(epsg, inplace=True)
    gdf.to_file(path, driver='ESRI Shapefile')

def remove_third_dimension(geom):
    """
    Function to remove the third dimension of a polygon Z geometry.

    Directly copied from:
    https://gis.stackexchange.com/questions/67210/convert-3d-wkt-to-2d-shapely-geometry
    """

    if geom.is_empty:
        return geom

    if isinstance(geom, shapely.geometry.Polygon):
        exterior = geom.exterior
        new_exterior = remove_third_dimension(exterior)

        interiors = geom.interiors
        new_interiors = []
        for intgr in interiors:
            new_interiors.append(remove_third_dimension(intgr))

        return shapely.geometry.Polygon(new_exterior, new_interiors)

    elif isinstance(geom, shapely.geometry.LinearRing):
        return shapely.geometry.LinearRing([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, shapely.geometry.LineString):
        return shapely.geometry.LineString([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, shapely.geometry.Point):
        return shapely.geometry.Point([xy[0:2] for xy in list(geom.coords)])

    elif isinstance(geom, shapely.geometry.MultiPoint):
        points = list(geom.geoms)
        new_points = []
        for point in points:
            new_points.append(remove_third_dimension(point))

        return shapely.geometry.MultiPoint(new_points)

    elif isinstance(geom, shapely.geometry.MultiLineString):
        lines = list(geom.geoms)
        new_lines = []
        for line in lines:
            new_lines.append(remove_third_dimension(line))

        return shapely.geometry.MultiLineString(new_lines)

    elif isinstance(geom, shapely.geometry.MultiPolygon):
        pols = list(geom.geoms)

        new_pols = []
        for pol in pols:
            new_pols.append(remove_third_dimension(pol))

        return shapely.geometry.MultiPolygon(new_pols)

    elif isinstance(geom, shapely.geometry.GeometryCollection):
        geoms = list(geom.geoms)

        new_geoms = []
        for geom in geoms:
            new_geoms.append(remove_third_dimension(geom))

        return shapely.geometry.GeometryCollection(new_geoms)

    else:
        raise RuntimeError(f'Currently this type of geometry is not supported: {type(geom)}')


def flatten_gdf(gdf):
    """
    Iterates over a geodataframe to remove the third dimension (ex.: POLYGON Z -> POLYGON).
    """

    for row, col in gdf.iterrows():
        # overwrite row with flattened 2D geometry
        gdf.loc[row, 'geometry'] = remove_third_dimension(col.geometry)

    return gdf


def filter_area(gdf_stock, gdf_surr, min_area):
    """Filter out area from stock above AREA_FILTER value and add to surroundings.
    
    inputs:
    gdf_stock: geodataframe with buildings to filter
    gdf_surr: geodataframe with surroundings to add to
    
    returns:
    gdf_stock: geodataframe with buildings above area filter"""
    # filt
        # add buildings below area filter to surroundings and delete from the gdfs
    gdf_surr = pd.concat([gdf_surr,
                          gdf_stock.loc[(gdf_stock.AREA_CALC * gdf_stock.floors_ag) < min_area, :]
                          ],
                         axis=0, ignore_index=True)
    gdf_stock = gdf_stock.loc[gdf_stock.AREA_CALC * gdf_stock.floors_ag >= min_area, :]

    return gdf_stock, gdf_surr
