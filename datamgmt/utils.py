"""
@author: Lennart Trentmann (lennart.trentmann@tum.de)
         Amedeo Ceruti (amedeo.ceruti@tum.de)
"""

import os
import logging
import warnings

import pandas as pd
import shapely.geometry
import geopandas as gpd


def import_shp(path, params):
    """
    Read preprocessed (in psql) shapefile (HU, LoD2) data and store in a GeoDataFrame.

    :param path: Path to shapefile
    :param params: Dictionary of parameters (e.g., EPSG)
    :returns: geopandas.DataFrame
    """
    gdf = gpd.read_file(path)

    if gdf.crs is None:
        gdf.crs = 'epsg:25832'
        warnings.warn(f'No CRS found in {path}. Set to {gdf.crs}')

    gdf.to_crs(epsg=params['EPSG'], inplace=True)
    return gdf


def import_csv(path, sep=",", fillna=0, index_col=None):
    """
    Read preprocessed zensus CSV and store in a DataFrame.

    :param path: CSV file path
    :param sep: Separator for CSV (default ",")
    :param fillna: Value to replace NaNs (default 0)
    :param index_col: Column to use as index
    :returns: pandas.DataFrame
    """
    df = pd.read_csv(path, sep=sep, engine='python', index_col=index_col)

    if fillna is not None:
        df = df.fillna(fillna)

    return df


def export_to_shp(gdf, path, epsg):
    """
    Export a GeoDataFrame to a shapefile.

    :param gdf: GeoDataFrame to export
    :param path: Output shapefile path
    :param epsg: EPSG code for CRS
    """
    gdf.to_crs(epsg, inplace=True)
    gdf.to_file(path, driver='ESRI Shapefile')


def remove_third_dimension(geom):
    """
    Remove the third dimension of a Polygon Z geometry.
    Source: https://gis.stackexchange.com/questions/67210/convert-3d-wkt-to-2d-shapely-geometry
    """
    if geom.is_empty:
        return geom

    if isinstance(geom, shapely.geometry.Polygon):
        exterior = geom.exterior
        new_exterior = remove_third_dimension(exterior)

        interiors = geom.interiors
        new_interiors = [remove_third_dimension(intgr) for intgr in interiors]

        return shapely.geometry.Polygon(new_exterior, new_interiors)

    elif isinstance(geom, shapely.geometry.LinearRing):
        return shapely.geometry.LinearRing([xy[0:2] for xy in geom.coords])

    elif isinstance(geom, shapely.geometry.LineString):
        return shapely.geometry.LineString([xy[0:2] for xy in geom.coords])

    elif isinstance(geom, shapely.geometry.Point):
        return shapely.geometry.Point([xy[0:2] for xy in geom.coords])

    elif isinstance(geom, shapely.geometry.MultiPoint):
        return shapely.geometry.MultiPoint([remove_third_dimension(pt) for pt in geom.geoms])

    elif isinstance(geom, shapely.geometry.MultiLineString):
        return shapely.geometry.MultiLineString([remove_third_dimension(line) for line in geom.geoms])

    elif isinstance(geom, shapely.geometry.MultiPolygon):
        return shapely.geometry.MultiPolygon([remove_third_dimension(pol) for pol in geom.geoms])

    elif isinstance(geom, shapely.geometry.GeometryCollection):
        return shapely.geometry.GeometryCollection([remove_third_dimension(g) for g in geom.geoms])

    else:
        raise RuntimeError(f'Geometry type not supported: {type(geom)}')


def flatten_gdf(gdf):
    """
    Remove third dimension (Z) from all geometries in a GeoDataFrame.
    """
    for row, col in gdf.iterrows():
        gdf.loc[row, 'geometry'] = remove_third_dimension(col.geometry)

    return gdf


def filter_area(gdf_stock, gdf_surr, min_area):
    """
    Filter buildings by minimum area and add smaller ones to surroundings.

    :param gdf_stock: GeoDataFrame with stock buildings
    :param gdf_surr: GeoDataFrame with surrounding buildings
    :param min_area: Minimum area threshold
    :returns: (filtered gdf_stock, updated gdf_surr)
    """
    gdf_surr = pd.concat([
        gdf_surr,
        gdf_stock.loc[(gdf_stock.AREA_CALC * gdf_stock.floors_ag) < min_area, :]
    ], axis=0, ignore_index=True)

    gdf_stock = gdf_stock.loc[(gdf_stock.AREA_CALC * gdf_stock.floors_ag) >= min_area, :]

    return gdf_stock, gdf_surr
