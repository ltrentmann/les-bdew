"""
Author: Lennart Trentmann
Contact: lennart.trentmann@tum.de
Date: 2023-11-22

Main script to generate ghd heat demand profile based on LOD2 data.
"""
import datetime
import matplotlib.pyplot as plt
import pandas as pd

pd.options.mode.copy_on_write = True
from warnings import simplefilter

import datetime
from datetime import time as settime 
import fastparquet

import demandlib.bdew as bdew
import geopandas as gpd
import os


simplefilter(action="ignore", category=pd.errors.PerformanceWarning)


# function to calculate demand profile according to BDEW standard load profile
def timeseries_calculation(demand, year, RUNID):

    # import epw file with pandas
    from epw import epw
    a = epw()
    a.read('inputdata/oikolab-%s.epw' % year)
    temperature = a.dataframe["Dry Bulb Temperature"]

    # create dictionary with annual demand for each building
    ann_demands_per_type = {}
    ann_el_demand_per_sector = {}

    for s, t in zip(demand['bdew_elec_profile'], demand['total_elec']):
        ann_el_demand_per_sector[s] = ann_el_demand_per_sector.get(s, 0) + t

    for k, v in ann_el_demand_per_sector.items():
        ann_el_demand_per_sector[k] = int(v)

    for i in demand.index:
        ann_demands_per_type[i] = demand['total_heat'][i]

    # datetime and holidays for region of demand profile
    from workalendar.europe import Germany
    cal = Germany()
    holidays = dict(cal.holidays(year))

    # Create DataFrame for 2022
    demand_ghd = pd.DataFrame(
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        )
    )

    demand_res = pd.DataFrame(
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        )
    )

    demand_elec = pd.DataFrame(
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        )
    )

    for i in ann_demands_per_type.keys():
        # calculate BDEW profile for each building 

        if demand["bdew_profile"][i] == 'EFH' or demand["bdew_profile"][i] == 'MFH':
            demand_res[i] = bdew.HeatBuilding(  # .bdew
                demand_res.index,
                holidays=holidays,
                temperature=temperature,
                shlp_type=demand["bdew_profile"][i],
                wind_class=1,   # check wind class
                annual_heat_demand=ann_demands_per_type[i],
                building_class=demand['building_class'][i],  
                name=demand["bdew_profile"][i],
                ww_incl=True,
            ).get_bdew_profile()
            # save peak value in demand dataframe column peak_heat
            demand.at[i, "peak_heat"] = demand_res[i].max()
            # change name of column to Name of demand
            demand_res.rename(columns={i: demand["Name"][i]}, inplace=True)

        else:
            demand_ghd[i] = bdew.HeatBuilding(
                demand_ghd.index,
                holidays=holidays,
                temperature=temperature,
                shlp_type=demand["bdew_profile"][i],
                wind_class=0,
                annual_heat_demand=ann_demands_per_type[i],
                building_class=0,
                name=demand["bdew_profile"][i],
                ww_incl=True,
            ).get_bdew_profile()
            # save peak value in demand dataframe
            demand.at[i, "peak_heat"] = demand_ghd[i].max()
            demand_ghd.rename(columns={i: demand["Name"][i]}, inplace=True)
    
    e_slp = bdew.ElecSlp(year, holidays=holidays)
    demand_elec = e_slp.get_profile(ann_el_demand_per_sector) 
    demand_elec = demand_elec.resample("H").mean()

    # export df_shape as shapefile
    output_dir = f"results/"
    # Create the directory if it doesn't exist
    os.makedirs(output_dir + f"{RUNID}/" + 'shapefile/', exist_ok=True)
    # Now you can save your shapefile
    demand.to_file(os.path.join(output_dir + f"{RUNID}/" + 'shapefile/', f'heat_demand_{RUNID}' + ".shp"))

    # sum up all columns of demand_ghd 
    demand_ghd["_ghd"] = demand_ghd.sum(axis=1)
    demand_res["_res"] = demand_res.sum(axis=1)

    # add column hour with values from 0 to 8760
    demand_ghd['hour'] = range(0, 8760)
    demand_res['hour'] = range(0, 8760)

    my_file_ghd = f'demand_ghd_{RUNID}'
    my_file_res = f'demand_res_{RUNID}'

    # write demand to csv
    demand_ghd.to_csv(export_path + f"{RUNID}/" + 'timeseries/' + my_file_ghd + ".csv", index=False, sep=';', decimal='.')
    demand_res.to_csv(export_path + f"{RUNID}/" + 'timeseries/' + my_file_res + ".csv", index=False, sep=';', decimal='.')
    demand_elec.to_csv(export_path + f"{RUNID}/" + 'timeseries/' + "demand_elec_" + ".csv", index=False, sep=';', decimal='.')

    demand_ghd.to_parquet(export_path + my_file_ghd + ".parquet", index=False)
    demand_res.to_parquet(export_path + my_file_res + ".parquet", index=False)
    demand_elec.to_parquet(export_path + "demand_elec_.parquet", index=False)

    # Create the directory if it doesn't exist
    os.makedirs(output_dir + f"{RUNID}/" + 'figures/', exist_ok=True)

    # plot demand sum and save as svg
    fig, ax = plt.subplots(figsize=(15, 10))
    plt.plot(demand_ghd["_ghd"])
    plt.ylabel('MW')
    plt.xlabel('hours')
    plt.savefig(output_dir + f"{RUNID}/" + 'figures/'+ my_file_ghd + ".svg")

    # plot demand sum and save as svg
    fig, ax = plt.subplots(figsize=(15, 10))
    plt.plot(demand_res["_res"])
    plt.ylabel('MW')
    plt.xlabel('hours')
    plt.savefig(output_dir + f"{RUNID}/" + 'figures/'+ my_file_res + ".svg")

    # plot elec demand and save as svg
    fig, ax = plt.subplots(figsize=(15, 10))
    plt.plot(demand_elec)
    plt.ylabel('MW')
    plt.xlabel('hours')
    plt.savefig(output_dir + f"{RUNID}/" + 'figures/' + "demand_elec_" + ".svg")

    return demand_ghd, demand_res
