"""
Author: Lennart Trentmann
Contact: lennart.trentmann@tum.de
Date: 2023-11-22

Script to generate yearly ghd heat demand in MWh.
"""

import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def demand(df_shape, spez_heat_bj, spez_elec_type,
           bdew_mapping, bdew_elec_mapping, spez_hot_water_mapping, 
           alpha_mapping, building_class_mapping, RUNID):

    # creat folder RUNID in results if not exists
    import os
    os.makedirs(f'results/{RUNID}/figures', exist_ok=True)
    os.makedirs(f'results/{RUNID}/shapefiles', exist_ok=True)
    os.makedirs(f'results/{RUNID}/timeseries', exist_ok=True)

    # list of building functions
    geb_list = [*spez_hot_water_mapping]


    # mapping of floor_heigth, alpha_hot_water, alpha and bdew profile to BD_FUNCTIO
    df_shape['spez_hot_water'] = df_shape['type_code'].map(spez_hot_water_mapping)
    df_shape['alpha'] = df_shape['type_code'].map(alpha_mapping)
    df_shape['bdew_profile'] = df_shape['type_code'].map(bdew_mapping)
    df_shape['bdew_elec_profile'] = df_shape['type_code'].map(bdew_elec_mapping)
    
    df_shape['building_class'] = df_shape.apply(
        lambda x: building_class_mapping.loc[x['age_code']][x['type_code']],
        axis=1
    )

    # sum AREA_ED * BD_STOREYS and group df_shape by BD_FUNCTIO
    df_shape['heated_area'] = (
        df_shape['AREA_CALC'] * 
        df_shape['floors_ag']
        ) * df_shape['alpha']

    # lookup spez_heat_bj for each building function and building age class
    df_shape['spez_heat'] = df_shape.apply(
        lambda x: spez_heat_bj.loc[x['type_code']][x['age_code']],
        axis=1
    )

    # lookup spez_elec for each building function and building age class
    df_shape['spez_elec'] = df_shape.apply(
        lambda x: spez_elec_type.loc[x['type_code']],
        axis=1
    )

    # calculate heat demand for each building
    df_shape['total_heat'] = (
            df_shape['heated_area'] *
            (df_shape['spez_heat']+
            df_shape['spez_hot_water']) / 1000
    )

    # calculate electricity demand for each building
    df_shape['total_elec'] = (
            df_shape['heated_area'] *
            df_shape['spez_elec'] / 1000
    )

    print(df_shape.head(5))
    # create column peak with zeros
    df_shape['peak_heat'] = 0

    # load google-maps as background
    fig, ax = plt.subplots(figsize=(15, 10))
    ax = df_shape.plot(column='total_heat', alpha=1, zorder=2)
    cx.add_basemap(
        ax,
        crs=df_shape.crs,
        source=cx.providers.CartoDB.Positron,
        alpha=1,
        zoom=12
    )
    # position legend below plot and horizontal
    im = ax.imshow(df_shape['total_heat'].values.reshape(1, -1), cmap='viridis')
    fig.colorbar(im, orientation="horizontal", pad=0.1)
    ax.set_axis_off()
    ax.set_title('total heat demand in MWh')
    # export df_shape as shapefile
    output_dir = r"results/"
    # Create the directory if it doesn't exist
    os.makedirs(output_dir + f"{RUNID}/" + 'figures/', exist_ok=True)
    
    my_file = 'building_demand_'
    plt.savefig(output_dir + f"{RUNID}/" + 'figures/' + my_file + ".svg")

    return df_shape
