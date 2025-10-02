"""
@author: Lennart Trentmann (lennart.trentmann@tum.de); 
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Calculate yearly heat and electricity demand profiles according to BDEW standard.
"""
import os
import datetime
import matplotlib.pyplot as plt
import pandas as pd
from warnings import simplefilter

import geopandas as gpd
import fastparquet
import demandlib.bdew as bdew

from epw import epw
from workalendar.europe import Germany

pd.options.mode.copy_on_write = True
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)


def timeseries_calculation(demand, year, RUNID):
    """
    Generate hourly heat and electricity demand profiles for buildings.

    Parameters
    ----------
    demand : GeoDataFrame
        Building data with heat/electricity demand and BDEW profiles.
    year : int
        Year for the demand profile.
    RUNID : str
        Unique identifier for output folders.

    Returns
    -------
    demand_ghd : DataFrame
        Hourly heat demand profile for non-residential buildings.
    demand_res : DataFrame
        Hourly heat demand profile for residential buildings.
    """

    # Load EPW weather file
    weather = epw()
    weather.read(f'inputdata/oikolab-{year}.epw')
    temperature = weather.dataframe["Dry Bulb Temperature"]

    # Initialize dictionaries for annual demand
    ann_demands_per_type = {i: demand['total_heat'][i] for i in demand.index}
    ann_el_demand_per_sector = {}
    for profile, elec in zip(demand['bdew_elec_profile'], demand['total_elec']):
        ann_el_demand_per_sector[profile] = ann_el_demand_per_sector.get(profile, 0) + elec
    ann_el_demand_per_sector = {k: int(v) for k, v in ann_el_demand_per_sector.items()}

    # Setup German calendar for holidays
    cal = Germany()
    holidays = dict(cal.holidays(year))

    # Create hourly index for the year
    hours_index = pd.date_range(
        datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
    )
    demand_ghd = pd.DataFrame(index=hours_index)
    demand_res = pd.DataFrame(index=hours_index)
    demand_elec = pd.DataFrame(index=hours_index)

    # Generate BDEW profiles for each building
    for i in demand.index:
        profile = demand["bdew_profile"][i]
        if profile in ["EFH", "MFH"]:
            df = bdew.HeatBuilding(
                demand_res.index,
                holidays=holidays,
                temperature=temperature,
                shlp_type=profile,
                wind_class=1,
                annual_heat_demand=ann_demands_per_type[i],
                building_class=demand['building_class'][i],
                name=profile,
                ww_incl=True,
            ).get_bdew_profile()
            demand_res[i] = df
            demand.at[i, "peak_heat"] = df.max()
            demand_res.rename(columns={i: demand["Name"][i]}, inplace=True)
        else:
            df = bdew.HeatBuilding(
                demand_ghd.index,
                holidays=holidays,
                temperature=temperature,
                shlp_type=profile,
                wind_class=1,
                annual_heat_demand=ann_demands_per_type[i],
                building_class=0,
                name=profile,
                ww_incl=True,
            ).get_bdew_profile()
            demand_ghd[i] = df
            demand.at[i, "peak_heat"] = df.max()
            demand_ghd.rename(columns={i: demand["Name"][i]}, inplace=True)

    # Generate electricity demand profile
    e_slp = bdew.ElecSlp(year, holidays=holidays)
    demand_elec = e_slp.get_profile(ann_el_demand_per_sector).resample("H").mean()

    # Create results directories
    base_dir = os.path.join("results", RUNID)
    for subfolder in ["shapefiles", "timeseries", "figures"]:
        os.makedirs(os.path.join(base_dir, subfolder), exist_ok=True)

    # Export building shapefile with peak_heat
    shapefile_path = os.path.join(base_dir, "shapefiles", f"heat_demand_{RUNID}.shp")
    demand.to_file(shapefile_path)

    # Sum all columns to get total demand per hour
    demand_ghd["_ghd"] = demand_ghd.sum(axis=1)
    demand_res["_res"] = demand_res.sum(axis=1)

    # Add hour column
    demand_ghd['hour'] = range(8760)
    demand_res['hour'] = range(8760)

    # File names
    gh_file = f"demand_ghd_{RUNID}"
    res_file = f"demand_res_{RUNID}"
    elec_file = f"demand_elec_{RUNID}"

    # Export CSV and parquet
    for df, name in [(demand_ghd, gh_file), (demand_res, res_file), (demand_elec, elec_file)]:
        df.to_csv(os.path.join(base_dir, "timeseries", f"{name}.csv"), index=False, sep=';', decimal='.')
        df.to_parquet(os.path.join(base_dir, f"{name}.parquet"), index=False)

    # Plot total heat and electricity demand
    for df, name, ylabel in [(demand_ghd, gh_file, "MW"), (demand_res, res_file, "MW"), (demand_elec, elec_file, "MW")]:
        fig, ax = plt.subplots(figsize=(15, 10))
        plt.plot(df.iloc[:, -1])
        plt.ylabel(ylabel)
        plt.xlabel('Hours')
        plt.savefig(os.path.join(base_dir, "figures", f"{name}.svg"))
        plt.close(fig)

    return demand_ghd, demand_res
