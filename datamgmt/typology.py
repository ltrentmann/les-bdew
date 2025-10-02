"""
@author: Lennart Trentmann (lennart.trentmann@tum.de)
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Returns a typology .dbf file of the imported building geodataframe.

Format:

Name
STANDARD
YEAR
1ST_USE = 'MULTI_RES'
1ST_USE_R = 1
2ND_USE = 'NONE'
2ND_USE_R = 0
3RD_USE = 'NONE'
3RD_USE_R = 0
"""

import numpy as np


def init(gdf):
    """Initialize typology file with default values."""
    gdf_2 = gdf.copy()

    # Assumption: only single-use buildings by default
    gdf_2.loc[:, '1ST_USE_R'] = np.ones(len(gdf))
    gdf_2.loc[:, '2ND_USE_R'] = np.zeros(len(gdf))
    gdf_2.loc[:, '3RD_USE_R'] = np.zeros(len(gdf))
    gdf_2.loc[:, '1ST_USE'] = 'MULTI_RES'
    gdf_2.loc[:, '2ND_USE'] = 'NONE'
    gdf_2.loc[:, '3RD_USE'] = 'NONE'
    gdf_2.loc[:, 'YEAR'] = np.ones(len(gdf)) * 1800

    return gdf_2


def assign(gdf, params):
    """
    Set building use depending on TABULA standard and mapping in parameters dictionary.
    """
    gdf_2 = gdf.copy(deep=True)

    # Assign use types based on building type
    for type_, uses in params['use_types'].items():
        if len(uses) == 1:
            gdf_2.loc[gdf_2['type_code'] == type_, '1ST_USE'] = uses[0]
        elif len(uses) == 2:
            gdf_2.loc[gdf_2['type_code'] == type_, '1ST_USE'] = uses[0]
            gdf_2.loc[gdf_2['type_code'] == type_, '2ND_USE'] = uses[1]
            gdf_2.loc[gdf_2['type_code'] == type_, '1ST_USE_R'] = 0.5
            gdf_2.loc[gdf_2['type_code'] == type_, '2ND_USE_R'] = 0.5
        elif len(uses) == 3:
            gdf_2.loc[gdf_2['type_code'] == type_, '1ST_USE'] = uses[0]
            gdf_2.loc[gdf_2['type_code'] == type_, '2ND_USE'] = uses[1]
            gdf_2.loc[gdf_2['type_code'] == type_, '3RD_USE'] = uses[2]
            gdf_2.loc[gdf_2['type_code'] == type_, '1ST_USE_R'] = 0.33
            gdf_2.loc[gdf_2['type_code'] == type_, '2ND_USE_R'] = 0.33
            gdf_2.loc[gdf_2['type_code'] == type_, '3RD_USE_R'] = 0.33
        else:
            raise ValueError('Too many uses for one building, maximum is 3.')

    # Map building ages to YEAR
    for row, value in gdf.iterrows():
        for age_code, year in params['tabula_ages']:
            if age_code == value.age_code:
                gdf_2.loc[row, 'YEAR'] = year

    return gdf_2


def compute(gdf, params):
    """
    Main function to compute the typology file from a geodataframe.
    """
    # Columns to keep in .dbf
    cols = [
        'Name', 'STANDARD', 'YEAR',
        '1ST_USE_R', '2ND_USE_R', '3RD_USE_R',
        '1ST_USE', '2ND_USE', '3RD_USE'
    ]

    # Initialize default values
    gdf_2 = init(gdf)

    # Assign building uses
    gdf_typology = assign(gdf_2, params)

    # Return only desired columns
    return gdf_typology.loc[:, cols]
