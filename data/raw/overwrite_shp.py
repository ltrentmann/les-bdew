import geopandas as gpd
import numpy as np

SHAPEFILE_IN = "data/raw/example_raw.shp"
SHAPEFILE_OUT = "data/raw/example_raw_bdew.shp"

def main(SHAPEFILE_IN, SHAPEFILE_OUT):
   gdf = gpd.read_file(SHAPEFILE_IN)

   print(gdf.head())

   # define dict to rename columns
   rename_dict = {
                  'GEOMETRY_C': 'geometry',
                  'TYPE_CODE': 'type_code',
                  'AGE_CODE': 'age_code',
                  'FLOORS_AG': 'floors_ag',
                  # 'NAME': 'Name',
               
                  }

   # HEIGHT_ED is not in all files
   if 'HEIGHT_CALC' not in gdf.columns:
      print("HEIGHT_CALC not in gdf.columns")
      gdf.loc[:, 'HEIGH_CALC'] = gdf.VOL_CALC / gdf.AREA_CALC

   # drop all columns not in keys
   '''try:
      # gdf = gdf.loc[:, rename_dict.keys()]
      gdf = gdf.rename(columns = rename_dict)
   except KeyError:
      print(gdf.columns.values)'''

   # if we have classified newest buildings, overwrite with 'L'
   gdf.loc[:, 'CONSTRUCTI'] = np.nan
   # for row, val in gdf.iterrows():
   #     if val.CONSTRUCTI == "2018+":
   #         gdf.loc[row, "CONSTRUCTI"] = 'L'

   gdf.to_file(SHAPEFILE_OUT, driver='ESRI Shapefile')

   # count unique instances in FUNCTION_N
   print(gdf.GML_ID.value_counts())


if __name__ == '__main__':
  
      main(SHAPEFILE_IN, SHAPEFILE_OUT)
