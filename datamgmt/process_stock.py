"""
@author: Lennart Trentmann (lennart.trentmann@tum.de)
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Cross Zensus 2011 data from a CSV file with the BDEW geodataframe.
Additionally, add refurbishment status with a given probability.
"""

import logging
import random
import warnings

import pandas as pd
import numpy as np

from datamgmt.utils import flatten_gdf, import_csv
from datamgmt.Parameters import Parameters


def sample_with_p(N, elements, weights):
    """
    Sample items (elements) N times from a probability distribution (weights).

    Args:
        N (int): Number of samples.
        elements (list): Elements to sample.
        weights (list): Probabilities for each element.

    Returns:
        list: Sampled elements.
    """
    samples = np.empty(N, dtype=object)

    for i in range(N):
        r = random.random()
        cum_prob = 0
        for j, value in enumerate(elements):
            cum_prob += weights[j]
            if cum_prob > r:
                samples[i] = value
                break
    return samples


def age_with_prob(gdf, number_per_age, age_categories):
    """
    Assign building ages to a GeoDataFrame according to a given number per age category.

    Args:
        gdf (GeoDataFrame): Building stock GeoDataFrame.
        number_per_age (np.array): Number of buildings per age category.
        age_categories (list): List of age categories.

    Returns:
        tuple: Modified GeoDataFrame and shuffled indices.
    """
    n_cum = np.cumsum(number_per_age, dtype=np.int32)
    gdf_shuffled = gdf.sample(frac=1)
    idxs = gdf_shuffled.index.values

    if len(number_per_age) != len(age_categories):
        raise ValueError(
            f'Number of census categories {len(number_per_age)} != {len(age_categories)}'
        )

    for j, val in enumerate(n_cum):
        if number_per_age[j] > 0:
            start_idx = 0 if j == 0 else n_cum[j - 1]
            gdf_shuffled.loc[idxs[start_idx:val], 'age_code'] = age_categories[j]

    return gdf_shuffled, idxs


def assign_ages(dfraster, gdf, parameters, assign_most_probable=False):
    """
    Assign building ages randomly in gdf given the number of buildings per age category
    from a raster (Zensus data).

    Args:
        dfraster (DataFrame): Raster data from Zensus.
        gdf (GeoDataFrame): Building stock GeoDataFrame.
        parameters (dict): Parameters for the code.
        assign_most_probable (bool): Assign most probable age category to all buildings.

    Returns:
        GeoDataFrame: Updated building stock GeoDataFrame.
    """
    gdf = gdf.copy(deep=True)
    dfraster = dfraster.copy(deep=True)

    gitter_ids = list(set(dfraster.gitter_id.tolist()))

    for gid in gitter_ids:
        gdf_grid = gdf.loc[gdf.CENS_GRID == gid, :]
        if gdf_grid.empty:
            logging.debug('No buildings in gitter id %s', gid)
            continue

        dfz = dfraster.loc[dfraster.gitter_id == gid, :]
        N_z = dfz.anzahl_ges.values[0]
        n_z = np.squeeze(dfz.drop(columns=['anzahl_ges', 'gitter_id']).values)
        p_z = n_z / N_z

        if N_z != np.cumsum(n_z)[-1]:
            raise ValueError(f'Cumsum != total buildings for gitter id {gid}')
        if len(parameters['p_age-residential']) != len(p_z):
            raise ValueError(f'Length mismatch of building ages for gitter id {gid}')

        if assign_most_probable:
            gdf_grid_copy = gdf_grid.copy(deep=True)
            if len(n_z) == 1:
                gdf_grid_copy['age_code'] = dfz.drop(columns=['anzahl_ges', 'gitter_id']).idxmax(axis=1).values
            else:
                maxs = dfz.drop(columns=['anzahl_ges', 'gitter_id']).idxmax(axis=1).values
                gdf_grid_copy['age_code'] = max(maxs)
        else:
            if N_z <= gdf.shape[0]:
                gdf_grid_copy, _ = age_with_prob(gdf, n_z, list(parameters['p_age-residential'].keys()))
            else:
                warnings.warn(f'More buildings in Zensus ({N_z}) than GIS ({gdf.shape[0]}) for raster id {gid}')
                x = n_z * (gdf.shape[0] / N_z)
                x_floor = np.floor(x)
                sums = sum(x - x_floor)

                gdf_grid_copy, idxs = age_with_prob(gdf, x_floor, list(parameters['p_age-residential'].keys()))

                if sums > 0:
                    p_rest = (x - x_floor) / sums
                    rest_buildings = gdf.shape[0] - int(np.sum(x_floor))
                    gdf_grid_copy.loc[idxs[-rest_buildings:], 'age_code'] = sample_with_p(
                        rest_buildings,
                        list(parameters['p_age-residential'].keys()),
                        np.squeeze(p_rest)
                    )

        gdf.loc[gdf['Name'].isin(gdf_grid_copy.Name.values), 'age_code'] = gdf_grid_copy.age_code.values

    return gdf


def find_closest(value, array):
    """
    Find closest point within an array to a given value.

    Args:
        value (float): Value to find closest point to.
        array (np.array): Vector to search.

    Returns:
        tuple: (index of closest element, distance)
    """
    d = np.abs(value - array)
    i = np.argmin(d)
    return i, d[i]


def assign_type_by_volume(df_tabula, gdf, parameters):
    """
    Assign TABULA building types based on LoD2 volume and age.

    Args:
        df_tabula (DataFrame): TABULA building type information.
        gdf (GeoDataFrame): Building stock GeoDataFrame.
        parameters (dict): Parameters.

    Returns:
        GeoDataFrame: Updated gdf with type_code, STANDARD, and volume_dif columns.
    """
    gdf = gdf.copy()
    gdf['type_code'] = ''
    gdf['STANDARD'] = ''
    gdf['volume_dif'] = 0

    for _, row in gdf.iterrows():
        df_filtered = df_tabula.loc[df_tabula.age_code == row.age_code]
        target_volume = row.VOL_CALC if not np.isnan(row.VOL_CALC) else row.AREA_CALC * parameters['netto_area_factor-residential']
        idx, vol_diff = find_closest(target_volume, df_filtered.heated_volume.values)
        code = df_filtered.building_type.values[idx]

        gdf.loc[gdf.Name == row.Name, ['type_code', 'STANDARD', 'volume_dif']] = [code, f"{code}_{row.age_code}", vol_diff]

    logging.debug('Assigned building types by volume')
    return gdf


def categorize(df_nonres, gdf):
    """
    Separate residential, non-residential, and surrounding buildings.

    Args:
        df_nonres (DataFrame): Non-residential mapping.
        gdf (GeoDataFrame): Building stock GeoDataFrame.

    Returns:
        tuple: (gdf_res, gdf_nonres, gdf_surr)
    """
    gdf_surr = gdf.loc[gdf['USE_CALC'].isna(), :]
    gdf_nona = gdf.loc[~gdf['USE_CALC'].isna(), :]
    gdf_res = gdf_nona.loc[gdf_nona['USE_CALC'].str.contains('Wohngeb'), :]
    gdf_nonres = gdf_nona.loc[~gdf_nona['USE_CALC'].str.contains('Wohngeb'), :]

    if len(gdf) != len(gdf_res) + len(gdf_nonres) + len(gdf_surr):
        raise ValueError('Lengths of categorized buildings do not match original length')

    return gdf_res, gdf_nonres, gdf_surr


def assign_type_by_function(df_iwu, gdf):
    """
    Assign non-residential building types from IWU mapping.

    Args:
        df_iwu (DataFrame): IWU mapping file.
        gdf (GeoDataFrame): Building stock GeoDataFrame.

    Returns:
        GeoDataFrame: Updated gdf.
    """
    gdf = gdf.copy()
    gdf['type_code'] = ''
    gdf['STANDARD'] = ''
    df_iwu = df_iwu.loc[df_iwu['iwu mapping'].notna(), :]

    for _, row in df_iwu.iterrows():
        gdf.loc[gdf.USE_CALC == row['building function'], 'type_code'] = row['iwu mapping']

    gdf['STANDARD'] = gdf['type_code'] + '_' + gdf['age_code']

    if gdf['type_code'].isna().any() or gdf['STANDARD'].isna().any():
        raise ValueError('Not all buildings have been assigned a type')

    return gdf


def residential_ages(df_census, gdf, parameters, assign_most_probable=True):
    """
    Assign ages and refurbishment for residential buildings.

    Args:
        df_census (DataFrame): Zensus raster data.
        gdf (GeoDataFrame): Building stock GeoDataFrame.
        parameters (dict): Parameters.

    Returns:
        GeoDataFrame: Updated gdf.
    """
    gdf = flatten_gdf(gdf)

    try:
        gdf_new = gdf.loc[gdf.CONSTRUCTI == 'L', :]
        gdf_old = gdf.loc[gdf.CONSTRUCTI != 'L', :]
    except AttributeError:
        gdf_old = gdf.copy()
        logging.debug('No CONSTRUCTI found; no new buildings included.')

    gdf_old['age_code'] = sample_with_p(
        len(gdf_old), list(parameters['p_age-residential'].keys()), list(parameters['p_age-residential'].values())
    )

    gdf_sampled = assign_ages(df_census, gdf_old, parameters, assign_most_probable=assign_most_probable)
    gdf_final = pd.concat([gdf_new, gdf_sampled], axis=0)
    return gdf_final


def nonresidential_ages(df_census, gdf, parameters):
    """
    Assign ages and refurbishment for non-residential buildings.

    Args:
        df_census (DataFrame): Zensus raster data.
        gdf (GeoDataFrame): Building stock GeoDataFrame.
        parameters (dict): Parameters.

    Returns:
        GeoDataFrame: Updated gdf.
    """
    gdf = flatten_gdf(gdf)

    try:
        gdf_new = gdf.loc[gdf.CONSTRUCTI == 'L', :]
        gdf_old = gdf.loc[gdf.CONSTRUCTI != 'L', :]
    except AttributeError:
        gdf_old = gdf.copy()
        logging.debug('No CONSTRUCTI found; no new buildings included.')

    gdf_old['age_code'] = sample_with_p(
        len(gdf_old), list(parameters['p_age-nonresidential'].keys()), list(parameters['p_age-nonresidential'].values())
    )

    gdf_final = pd.concat([gdf_new, gdf_old], axis=0)
    gdf_final = assign_ages(df_census, gdf_final, parameters, assign_most_probable=True)
    gdf_final['age_code'] = gdf_final['age_code'].map(parameters['age_mapping-nonres'])

    return gdf_final


def assign_refurbishment_status(gdf, df_tabula):
    """
    Add refurbishment status to buildings based on probabilities.

    Args:
        gdf (GeoDataFrame): Building stock.
        df_tabula (DataFrame): TABULA building types with probabilities.

    Returns:
        GeoDataFrame: Updated gdf.
    """
    for idx, row in gdf.iterrows():
        std = row.STANDARD
        p_nr, p_ar = df_tabula.loc[df_tabula['code'] == std, ['p_normal_ref', 'p_advanced_ref']].values.squeeze()
        w = [1 - (p_nr + p_ar), p_nr, p_ar]
        choice = random.choices([std, f"{std}_NR", f"{std}_AR"], weights=w, k=1)[0]
        gdf.at[idx, 'STANDARD'] = choice

    return gdf


def edit_surroundings(gdf, parameters):
    """
    Simplify surrounding buildings and filter by height.

    Args:
        gdf (GeoDataFrame): Building stock.
        parameters (dict): Parameters.

    Returns:
        GeoDataFrame: Updated gdf.
    """
    gdf = gdf.loc[~gdf.USE.isin(['Überdachung', 'Garage', 'Brücke']), :]
    min_height = max(parameters.get('HEIGHT_SURR_FILTER', 1), 1)
    if min_height > 1:
        gdf = gdf.loc[gdf.height_ag > min_height, :]
    else:
        warnings.warn('HEIGHT_SURR_FILTER < 1m, enforcing 1m')
        gdf = gdf.loc[gdf.height_ag > 1, :]
    return gdf


def assign_categories(gdf, zensus_path, tabula_path, nonres_path, parameters):
    """
    Assign building ages and types based on Zensus and TABULA data.

    Args:
        gdf (GeoDataFrame): Building stock.
        zensus_path (str): Path to Zensus raster CSV.
        tabula_path (str): Path to TABULA building types CSV.
        nonres_path (str): Path to non-residential IWU types CSV.
        parameters (dict): Parameters.

    Returns:
        tuple: (residential_gdf, nonresidential_gdf, surroundings_gdf)
    """
    df_census = import_csv(zensus_path, sep=None, index_col=0)
    df_tabula = import_csv(tabula_path, sep=None)
    df_nonres = pd.read_csv(nonres_path, sep=";", index_col=0)

    gdf_res, gdf_nonres, gdf_surr = categorize(df_nonres, gdf)
    gdf_nonres2 = nonresidential_ages(df_census, gdf_nonres, parameters)
    gdf_nonres3 = assign_type_by_function(df_nonres, gdf_nonres2)

    gdf_res2 = residential_ages(df_census, gdf_res, parameters, assign_most_probable=True)
    gdf_res3 = assign_type_by_volume(df_tabula, gdf_res2, parameters)
    gdf_res4 = assign_refurbishment_status(gdf=gdf_res3, df_tabula=df_tabula)

    return gdf_res4, gdf_nonres3, gdf_surr
