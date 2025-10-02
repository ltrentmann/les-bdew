# -*- coding: utf-8 -*-
"""
@author: Lennart Trentmann (lennart.trentmann@tum.de); 
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Script to generate yearly heat and electricity demand in MWh.
"""

import os
import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datamgmt.Parameters import Parameters as Params

def demand(
    df_shape, 
    RUNID
):
    """
    Calculate heat and electricity demand per building and generate a heat map.

    Parameters
    ----------
    df_shape : GeoDataFrame
        Shapefile with building geometries and attributes.
    RUNID : str
        Identifier for results folder.
    
    Returns
    -------
    df_shape : GeoDataFrame
        Updated GeoDataFrame with heat and electricity demand.
    """
    # init parameters object
    params = Params()

    # Create results folders
    base_dir = os.path.join("results", RUNID)
    for subfolder in ["figures", "shapefiles", "timeseries"]:
        os.makedirs(os.path.join(base_dir, subfolder), exist_ok=True)

    # Map parameters to building types
    df_shape['spez_hot_water'] = df_shape['type_code'].map(params.spez_hot_water_mapping)
    df_shape['alpha'] = df_shape['type_code'].map(params.alpha_mapping)
    df_shape['bdew_profile'] = df_shape['type_code'].map(params.bdew_mapping)
    df_shape['bdew_elec_profile'] = df_shape['type_code'].map(params.bdew_elec_mapping)
    df_shape['building_class'] = df_shape.apply(
        lambda x: params.building_class_mapping.loc[x['age_code']][x['type_code']],
        axis=1
    )

    # Calculate heated area
    df_shape['heated_area'] = df_shape['AREA_CALC'] * df_shape['floors_ag'] * df_shape['alpha']

    # sum heat demand for 1st and 2nd use if they exist
    def calculate_spez_heat(row, params):
        total_heat = 0
        for use in ['1ST_USE', '2ND_USE']:
            use_val = row.get(use)
            if pd.notna(use_val) and use_val != 'NONE':
                # multiply by the share if available (e.g., '1ST_USE_R')
                share = row.get(f'{use}_R', 1)  # default 1 if not present
                total_heat += params.spez_heat_bj.loc[use_val, row['age_code']] * share
        return total_heat

    df_shape['spez_heat'] = df_shape.apply(lambda x: calculate_spez_heat(x, params), axis=1)

    df_shape['spez_elec'] = df_shape.apply(
        lambda x: params.spez_elec_type.loc[x['type_code']], 
        axis=1
    )

    # Calculate total heat and electricity demand in MWh
    df_shape['total_heat'] = df_shape['heated_area'] * (df_shape['spez_heat'] + df_shape['spez_hot_water']) / 1000
    df_shape['total_elec'] = df_shape['heated_area'] * df_shape['spez_elec'] / 1000

    # Initialize peak column
    df_shape['peak_heat'] = 0

    # Plot heat demand map
    fig, ax = plt.subplots(figsize=(15, 10))
    df_shape.plot(column='total_heat', alpha=1, ax=ax, zorder=2)
    cx.add_basemap(
        ax,
        crs=df_shape.crs,
        source=cx.providers.CartoDB.Positron,
        alpha=1,
        zoom=12
    )

    # Add horizontal colorbar
    im = ax.imshow(df_shape['total_heat'].values.reshape(1, -1), cmap='viridis')
    fig.colorbar(im, orientation="horizontal", pad=0.1)
    ax.set_axis_off()
    ax.set_title('Total heat demand in MWh')

    # Save figure
    figure_path = os.path.join(base_dir, "figures", "building_demand.svg")
    plt.savefig(figure_path, bbox_inches='tight')

    # Optional: export updated shapefile
    shapefile_path = os.path.join(base_dir, "shapefiles", "building_demand.shp")
    df_shape.to_file(shapefile_path)

    return df_shape
