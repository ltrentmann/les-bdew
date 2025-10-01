"""
Author: Amedeo Ceruti
Contact: amedeo.ceruti@tum.de
Date: 2022-21-11

Cross the zensus 2011 data from a csv file with the cea geodataframe. 
Additionally add refurbishment status with a given probability.

"""

import logging
import random
import warnings

import pandas as pd
# import geopandas as gpd
import numpy as np
# import deepcopy as copy

from datamgmt.utils import flatten_gdf, import_csv

__author__ = "Amedeo Ceruti"
# __copyright__ = "Copyright 2022, TU Munich"
__credits__ = ["Amedeo Ceruti"]
# __license__ = "MIT"
__version__ = "0.1.1"
__maintainer__ = "Amedeo Ceruti"
__email__ = "amedeo.ceruti@tum.de"
__status__ = "Dev"


def sample_with_p(N, elements, weights):
    """sample items (elements) N times from a probability distribution (weights).

    source: https://stackoverflow.com/questions/29426266/python-random-sample-with-probabilities

    Args:
        N (integer): Number of samples to make.
        elements (list): Elements to assign with a given probability.
        weights (list): floats in [0,1]. 

    Returns:
        samples (list): Sampled elements
    """

    samples = np.empty(N, dtype=object)  # create empty array of objects

    r = 0
    temp = 0
    for i in range(N):
        r = random.random()  # random number in [0,1]
        temp = 0
        for j, value in enumerate(list(elements)):  # cum prob
            temp += list(weights)[j]
            if temp>r:  # if in interval, store and break to next
                samples[i] = value
                break

    return samples


def age_with_prob(gdf, number_per_age, age_categories):
    """ Assigns building ages from a  given list to a given number of buildings
    in a dataframe. Assigns number of buildings to each age category randomly
    with probability in age_categories, the rest purely randomly.
    
    Inputs: 
    df: dataframe with GIS data
    number_per_age: np.array of integers of dim (1, :). number of buildings for
    each age category.
    age_categories = list of strings. all age categories

    Outputs: 
    df (geopandas. dataframe) : modified df.age_code column
    idxs: list of integers. shuffled indexes
    """

    n_cum = np.cumsum(number_per_age, dtype=np.int32)
    gdf_shuffled = gdf.sample(frac = 1)  # shuffle randomly
    idxs = gdf_shuffled.index.values # Schuffled indexes

    # check for consistency
    if len(number_per_age) != len(age_categories):
        raise ValueError(f'Vector of census categories {len(number_per_age)} != {len(age_categories)} age categories')

    for j, value in enumerate(n_cum):  # iterate over the building age vector
        if number_per_age[j] > 0: # if a given category is > 0
            if j == 0:
                # assign to intverval of num buildings
                gdf_shuffled.loc[idxs[0:value], 'age_code'] = list(age_categories)[j]
            else:
                gdf_shuffled.loc[idxs[n_cum[j-1]:value], 'age_code'] = list(age_categories)[j]
    return gdf_shuffled, idxs


def assign_ages(dfraster, gdf, parameters, assign_most_probable=False):
    """
    Assign building ages randomly in gdf containing the building dataset given 
    the number of buildings for each age category a raster category (dataframe).

    Args:
        dfraster (pandas.DataFrame): raster data from zensus
        gdf (geopandas.DataFrame): building stock dataframe
        parameters (datamgmt.Parameters.Params()): Parameters for the code.
        assign_most_probable (bool): Assign most probable age category to all buildings in gdf_residential.
    
    Returns:
        gdf (geopandas.DataFrame): Updated building stock dataframe
    """
    # https://stackoverflow.com/questions/43777243/how-to-split-a-dataframe-in-pandas-in-predefined-percentages

    gdf = gdf.copy(deep=True )
    dfraster = dfraster.copy(deep=True)

    # get gitter ids and store in list
    # conserve only unique values by converting to set and back
    gitter_ids = list(set(dfraster.gitter_id.tolist()))

    for id_ in gitter_ids:  # iterate gitter id
        # filter for gitter id
        gdf_ = gdf.loc[gdf.CENS_GRID == id_, :]
        # if none in the grid, skip iteration of loop
        if gdf_.shape[0] == 0:
            logging.debug('No buildings in gitter id %s', id_)
            continue
        dfz = dfraster.loc[dfraster.gitter_id == id_, :]  # store filtered row

        # total number of buildings in zensus raster
        N_z = dfz.anzahl_ges.values
        # ratio of buildings per category
        n_z = np.squeeze(dfz.drop(columns = ['anzahl_ges', 'gitter_id']).values)  
        p_z = n_z / N_z  # number of buildings per category

        # sanity checks
        if N_z != np.cumsum(n_z)[-1]:
            raise Exception(
                f'Should not have arrived here, cumsum != total number of buildings in zensus data gitter id : {id_}'
                )
        if len(parameters['p_age-residential']) != len(np.squeeze(p_z)):
            raise Exception(
                f'Length of list of building ages is not equal to list of zensus data building age numbers. gitter id : {id_}'
                )

        if assign_most_probable:
                    # assign buildings to age category by most probable
            gdf1 = gdf_.copy(deep=True)
            # select most probable age category
            if len(n_z) == 1:
                gdf1.loc[:, 'age_code'] = dfz.drop(columns = ['anzahl_ges', 'gitter_id']).idxmax(axis=1).values
            elif len(n_z) > 1:
                # select most recent (larger alphabetical order) age category
                maxs = dfz.drop(columns = ['anzahl_ges', 'gitter_id']).idxmax(axis=1).values
                gdf1.loc[:, 'age_code'] = max(maxs)
        else:
            # assign buildings to age category randomly in required numbers
            if N_z <= gdf.shape[0]:  # case 1 and 2: <= houses in zensus than in GIS data
                # assign randomly to given number of buildings
                gdf1, _ = age_with_prob(gdf, np.squeeze(n_z), parameters['p_age-residential'].keys())
            elif N_z > gdf.shape[0]:  # case 3: more buildings in zensus
                warnings.warn(
                    f'More buildings in Zensus ({N_z}) than in GIS data ({gdf.shape[0]}) for raster id {id_}'
                    )
                x = np.squeeze(n_z) * (gdf.shape[0]/N_z)  # number of buildings
                x_floor = np.floor(x)  # round down
                sums = sum(x - x_floor)

                # assign to round number of buildings
                gdf1, idxs = age_with_prob(
                    gdf, np.squeeze(x_floor), parameters['p_age-residential'].keys()
                    )

                # avoid div by 0 and other assignment issues due to 0s
                if sums > 0:
                    # rest = Probability of being age x
                    p_rest = (x - x_floor)/sums
                    # assign the rest (so indexes[number of building to end]) with 
                    # the rest of probability
                    # https://stackoverflow.com/questions/1388818/how-can-i-compare-two-lists-in-python-and-return-matches
                    rest_buildings = gdf.shape[0] - int(np.sum(x_floor))
                    gdf1.loc[idxs[-rest_buildings:], 'age_code'] = sample_with_p(
                        rest_buildings,
                        parameters['p_age-residential'].keys(),
                        np.squeeze(p_rest)
                        )

        # overwrite assigned values in building dataset
        gdf.loc[gdf['Name'].isin(
            gdf1.Name.values), 'age_code'] = gdf1.age_code.values
    return gdf


def find_closest(value, array):
    """Find closest point within an array to a given value.
    
    Find closest point to a value within a numpy.array and return its location 
    index.

    Args:
        value (float): value to find closest point to.
        array (np.array): vector where locations are.

    Returns:
        i (integer): index of array of minimal distance
        d[i] (float) : absolute minimal distance value
    """
    d = np.abs(value - array)
    i = np.argmin(d)
    return i, d[i]


def assign_type_by_volume(df, gdf, parameters):
    """    Assign TABULA building types to GIS data.
    
    Assign TABULA building types (single family home, multi family home, 
    apartment block, terraced home) depending on mean TABULA building volume
    and measured LoD2 envelope volume. ASSUMPTION: building age is known.

    Args:
        df (pandas.DataFrame): TABULA categories information.
        gdf (geopandas.DataFrame): building stock GIS data
        parameters (datamgmt.Parameters.Params()): Parameters for the code.

    Returns:
        _type_: _description_
    """
    # init new column for building type
    gdf.loc[:, 'type_code'] = ''
    gdf.loc[:, 'volume_dif'] = 0
    gdf.loc[:, 'STANDARD'] = ''

    # create copy we will overwrite
    gdf2 = gdf.copy()

    # drop NaN values from LoD1 dataset
    # gdf_nona = gdf.dropna(axis = 0, subset = ['VOLUME'])

    for _, value in gdf.iterrows():

        # filter out current age code (ASSUMPTION: AGE CODE IS TRUE)
        dffiltered = df.loc[df.age_code == value.age_code]

        if np.isnan(value['VOL_CALC']):
            # find location of closest category w/ area
            idx, vol_diff = find_closest(
                value.AREA_CALC * parameters['netto_area_factor'],
                np.squeeze(dffiltered.netto_area.values)
                )
        else:
            # find location of closest category
            # MFH E gives problems
            idx, vol_diff = find_closest(
                value.VOL_CALC,
                np.squeeze(dffiltered.heated_volume.values)
                )

        # store building type value
        code = dffiltered.building_type.values[idx]
        # overwrite with chosen type
        gdf2.loc[gdf2.Name == value.Name, 'type_code'] = code
        gdf2.loc[gdf2.Name == value.Name, 'volume_dif'] = vol_diff
        gdf2.loc[gdf2.Name == value.Name, 'STANDARD'] = code + '_' + value.age_code

        logging.debug('assigned building types by volume')
    return gdf2


def categorize(df_nonres, gdf):
    """Separate residential, non residential and surrounding buildings based on a dataframe which
    defines the mapping of different categories to nonresidential or residential.

    Args:
        df_nonres (pandas.DataFrame): dataframe with mapping of nonresidential categories.
        gdf (geopandas.DataFrame): building stock dataframe.
    
    Returns:
        gdf_res (geopandas.DataFrame): residential buildings
        gdf_nonres (geopandas.DataFrame): non residential buildings
        gdf_surr (geopandas.DataFrame): surrounding buildings
    """
    df_nonres = df_nonres.copy(deep=True)

    # non heated buildings
    # to_surroundings = df_nonres.loc[
    #     ((df_nonres['heated'] == 'no') | (df_nonres['iwu mapping'].isna())), 'building function'].unique()
    # gdf_surr = gdf.loc[gdf['FUNCTION_N'].isin(to_surroundings), :]
    # # residential buildings
    # gdf_res = gdf.loc[gdf['FUNCTION_N'].str.contains('Wohngeb'), :]

    gdf_surr = gdf.loc[gdf['USE_CALC'].isna(), :]
    gdf_nona = gdf.loc[~gdf['USE_CALC'].isna(), :]
    gdf_res = gdf_nona.loc[gdf_nona['USE_CALC'].str.contains('Wohngeb'), :]

    # non residential buildings
    # to_nonres = df_nonres.loc[~df_nonres['iwu mapping'].isna(), 'Building function'].unique()
    gdf_nonres = gdf_nona.loc[~gdf_nona['USE_CALC'].str.contains('Wohngeb'), :]

    # check if lengths of all three add up to the original length
    if len(gdf) != len(gdf_res) + len(gdf_nonres) + len(gdf_surr):
        raise ValueError('Lengths of residential, non residential and surroundings do not add up to original length')

    return gdf_res, gdf_nonres, gdf_surr


def assign_type_by_function(df, gdf):
    """    Assign nonresidential building types to GIS data.
    
    Assign IWU building types depending on the DE_type-to-IWU.csv mapping, baed on assumptions from
    building function in the database. Assumes age_code is not empty.

    Args:
        df (pandas.DataFrame): IWU mapping information (generall ./databases/DE_type-to-IWU.csv).
        gdf (geopandas.DataFrame): building stock GIS data.
        parameters (datamgmt.Parameters.Params()): Parameters for the code.

    Returns:
        _type_: _description_
    """
    # init new column for building type
    gdf.loc[:, 'type_code'] = ''
    gdf.loc[:, 'STANDARD'] = ''

    # create copy we will overwrite
    gdf2 = gdf.copy()
    df = df.loc[df['iwu mapping'].notna(), :]

    # assign type code depending on FUNCTION_N
    for _, value in df.iterrows():
        # overwrite with chosen type
        gdf2.loc[gdf2.USE_CALC == value['building function'], 'type_code'] = value['iwu mapping']

    # assign type code depending on FUNCTION_N
    for idx, value in gdf2.iterrows():
        gdf2.loc[idx, 'STANDARD'] = value['type_code'] + '_' + value['age_code']

    # check if all buildings have been assigned a type
    if any((gdf2.type_code == '') | (gdf2.STANDARD == '')):
        raise ValueError('Not all buildings have been assigned a type')

    return gdf2


def residential_ages(df, gdf, parameters, assign_most_probable=True):
    """ Add refurbishment level.
    
    Cross the zensus dataframe (raster id with age distributions) 
    with the geodataframe which contains the buildings to send to CEA.


    Args:
        df (string): path to TABULA builing type dataframe.
        gdf (geopandas.DataFrame): building stock dataframe.
        parameters (datamgmt.Params): Parameters of the package.

    Returns:
        geopandas.DataFrame: Updated dataframe containing refurbished buildings
    """

    # remove any 3rd dimension (ex.: POLYGON Z to POLYGON)
    gdf = flatten_gdf(gdf)

    # new  buildings (we are certain of those tagged with 'L' in CONSTRUCTI)
    try:
        gdf_new = gdf.loc[gdf.CONSTRUCTI == 'L', :]
        gdf_old = gdf.loc[gdf.CONSTRUCTI != 'L', :]
    except AttributeError:
        gdf_old = gdf.copy()
        logging.debug('Careful, no CONSTRUCTI found, therefore no new buildings included.')

    #  first fill with probability distribution of bavarian building strock
    gdf_old['age_code'] = sample_with_p(len(gdf_old['age_code'].values),
        parameters['p_age-residential'].keys(),
        parameters['p_age-residential'].values()
        )

    # assign each building age randomly according to probability distribution of raster
    gdf_sampled = assign_ages(df, gdf_old, parameters, assign_most_probable=assign_most_probable)

    # concatenate both geodataframes on row axis
    gdf_final = pd.concat([gdf_new, gdf_sampled], axis=0)

    return gdf_final


def nonresidential_ages(df, gdf, parameters):
    """ Add refurbishment level.
    
    Cross the zensus dataframe (raster id with age distributions) 
    with the geodataframe which contains the buildings to send to CEA.


    Args:
        df (string): path to TABULA builing type dataframe.
        gdf (geopandas.DataFrame): building stock dataframe.
        parameters (datamgmt.Params): Parameters of the package.

    Returns:
        geopandas.DataFrame: Updated dataframe containing refurbished buildings
    """

    # remove any 3rd dimension (ex.: POLYGON Z to POLYGON)
    gdf = flatten_gdf(gdf)

    # new  buildings (we are certain of those tagged with 'L' in CONSTRUCTI)
    try:
        gdf_new = gdf.loc[gdf.CONSTRUCTI == 'L', :]
        gdf_old = gdf.loc[gdf.CONSTRUCTI != 'L', :]
    except AttributeError:
        gdf_old = gdf.copy()
        logging.debug('Careful, no CONSTRUCTI found, therefore no new buildings included.')

    #  first fill with probability distribution of bavarian building stock
    gdf_old['age_code'] = sample_with_p(len(gdf_old['age_code'].values),
        parameters['p_age-nonresidential'].keys(),
        parameters['p_age-nonresidential'].values()
        )

    # concatenate both geodataframes on row axis
    gdf_final = pd.concat([gdf_new, gdf_old], axis=0)

    gdf_final = assign_ages(df, gdf_final, parameters, assign_most_probable=True)
    # map all age_codes from tabula to iwu categories
    gdf_final.loc[:, 'age_code'] = gdf_final.age_code.map(parameters['age_mapping-nonres'])

    return gdf_final


def assign_refurbishment_status(gdf, df):
    """Add refurbishment level to gdf.

    Assigns a refurbishment standard with a given probability 
    (p_nromal_ref or p_advanced_ref) in tabula_path csv file.


    Args:
        gdf (geopandas.DataFrame): building stock information
        df (pandas.DataFrame): TABULA building type informatio

    Returns:
        geopandas.DataFrame: updated building stock
    """
    # iterate over gdf rows
    for row, value in gdf.iterrows():
        # given building standard
        std = value.STANDARD
        # probability of having a given refurbishment level
        [p_nr, p_ar] = df.loc[df['code'] == std, ['p_normal_ref', 'p_advanced_ref']].values.squeeze()
        w = [1-(p_nr+p_ar), p_nr, p_ar]
        choice = random.choices(
            [std, std+'_NR', std+'_AR'],
            weights=w,
            k=1
            )
        gdf.loc[[row], 'STANDARD'] = choice

    return gdf


def edit_surroudings(gdf, parameters):
    """Simplify surroundings.
    
    Drop some stuff to reduce surroundings and drop surrounding buildings less
    than 4m.
    
    Args:
        gdf (geopandas.DataFrame): building stock information
        parameters (datamgmt.Params): Parameters of the package.
    
    Returns:
        geopandas.DataFrame: updated building stock"""

    gdf = gdf.loc[gdf.USE != "Überdachung", :]
    gdf = gdf.loc[gdf.USE != "Garage", :]
    gdf = gdf.loc[gdf.USE != "Brücke", :]

    # drop surrounding buildings less than 4m 
    # (less than 1 m will throw an error in CEA)
    if parameters['HEIGHT_SURR_FILTER'] > 1:
        gdf = gdf.loc[gdf.height_ag > parameters['HEIGHT_SURR_FILTER'], :]
    else:
        warnings.warn('HEIGHT_SURR_FILTER is less than 1m, enforcing 1m')
        gdf = gdf.loc[gdf.height_ag > 1, :]

    # gdf = gdf.loc[gdf.VOLUME > parameters['VOLUME_FILTER'], :]
    return gdf


def assign_categories(gdf, zensus_path, tabula_path, nonres_path, parameters):
    """
    Assigns ages to each building in the geodataframe 
    according to raster probabilities from Zensus 2011.
    """

    # Import zensus raster file
    df_census =  import_csv(zensus_path, sep=None, index_col=0)
    # Import TABULA file
    df_tabula = import_csv(tabula_path, sep=None)
    # Import non residential IWU types
    df_nonres = pd.read_csv(nonres_path, sep=";", index_col=0, header=0)

    logging.debug('imported zensus, nonres and tabula .csv')

    # process the information, update and aggregate age categories
    # so that it corresponds with CEA database ages

    # assign categories according to raster   
    gdf_res, gdf_nonres, gdf_surr = categorize(df_nonres, gdf)

    # edit surroundings
    # gdf_surr2 = edit_surroudings(gdf_surr, parameters)

    # assign building ages to nonresidential buildings
    gdf_nonres2 = nonresidential_ages(df_census, gdf_nonres, parameters)
    logging.debug('assigned non res building ages')
    gdf_nonres3 = assign_type_by_function(df_nonres, gdf_nonres2)
    logging.debug('assigned building types')

    gdf_res2 = residential_ages(df_census, gdf_res, parameters, assign_most_probable=True)
    logging.debug('assigned res building ages')
    gdf_res3 = assign_type_by_volume(df_tabula, gdf_res2, parameters)
    logging.debug('assigned building types')
    gdf_res4 = assign_refurbishment_status(gdf=gdf_res3, df=df_tabula)
    logging.debug('assigned refurbishment status')

    return gdf_res4, gdf_nonres3, gdf_surr 
 