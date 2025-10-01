"""
Author: Amedeo Ceruti
Contact: amedeo.ceruti@tum.de
Date: 2022-09-05

returns a typology .dbf file of the imported building geodataframe.

Format:

```
Name
STANDARD
YEAR
1ST_USE = 'MULTI_RES'
1ST_USE_R = 1
2ND_USE = 'NONE'
2ND_USE_R = 0
3RD_USE = 'NONE'
3RD_USE_R = 0
```
"""

import numpy as np

def init(gdf):
    """Initialize typology file with empty values."""
    # copy gdf to work with it.
    gdf_2 = gdf.copy()

    # initialize values, assumption: only single use buildings.
    gdf_2.loc[:, '1ST_USE_R'] = np.ones([len(gdf)])
    gdf_2.loc[:, '2ND_USE_R'] = np.zeros([len(gdf)])
    gdf_2.loc[:, '3RD_USE_R'] = np.zeros([len(gdf)])
    gdf_2.loc[:, '1ST_USE'] = 'MULTI_RES'
    gdf_2.loc[:, '2ND_USE'] = 'NONE'
    gdf_2.loc[:, '3RD_USE'] = 'NONE'
    gdf_2.loc[:, 'YEAR'] = np.ones([len(gdf)])*1800
    return gdf_2


def assign(gdf, params):
    """
    Set building use depending on TABULA standard and mapping in parameters 
    dictionary.
    """
    # copy gdf to work with it.
    gdf_2 = gdf.copy(deep=True)
    # iterate over rows and assign depending on case
    # map params values to keys in gdf.
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

    for row, value in gdf.iterrows():
        for i in params['tabula_ages']:
            if i[0] == value.age_code:
                gdf_2.loc[row, 'YEAR'] = i[1]
    return gdf_2


def compute(gdf, params):
    """
    main function which computes the typology file from a geodataframe.
    """
    # column names to conserve in .dbf file
    cols = [
        'Name', 'STANDARD', 'YEAR',
        '1ST_USE_R', '2ND_USE_R', '3RD_USE_R',
        '1ST_USE', '2ND_USE', '3RD_USE'
        ]

    # filter
    # gdf = gdf.loc[gdf.FUNCTION_N.str.contains('Wohngeb'), :]

    # apply uses function
    gdf_2 = init(gdf)

    # filter out columns we want to conserve in typology file
    gdf_typology = assign(gdf_2, params)

    return gdf_typology.loc[:, cols]
