# GIS-based bdew SLP calculation for german residential and nonresidential buildings

## Description

Package to generate heat and electricity timeseries with demandlib based on LOD2 database

- Date: 22.11.2023
- Project: <https://www.enargus.de/pub/bscw.cgi/?op=enargus.eps2&q=HEAT2Q&v=10&id=8909299>

## Workflow
Here you can see the overall workflow of generating building specific load profiles for heat and electricity:

![Overview](https://github.com/ltrentmann/les-bdes/blob/main/description/2024-12-18_data-and-slp-calculation.drawio.svg "Overview")


## Timeseries calcualtion
The following listed attributes from demandlib have to be specified:

Attributes from demandlib: <br />
| **holidays**: holidays from workalender python package according to defined <br />
| **year**: year <br />
| **temperature**: temperature timeseries from weather data file,<br />
| **shlp_type**: "bdew_profile" according to mapping in building_class_mapping.csv,<br />
| **wind_class**: 1,<br />
| **annual_heat_demand**: "ann_demands_per_type" calculated,<br />
| **building_class**: 'building_class' from shape file,  <br />
| **name**: "bdew_profile" according to mapping in building_class_mapping.csv,<br />
| **ww_incl**: True, includes hot water<br />

## Description of timeseries generation according to demandlib:
Heat profiles are created according to the approach described in the corresponding BDEW guideline.

The method was originally established in this `PhD Thesis at TU Munich <https://mediatum.ub.tum.de/doc/601557/601557.pdf>`.

The approach for generating heat demand profiles is described in section 4.1 (Synthetic load profile approach).

$$ Q_{day}(\theta) = KW \cdot h(\theta) \cdot F \cdot SF $$

| **KW**: Kundenwert (customer value). Daily consumption of customer at $\approx 8 ^\circ C$, depending on SLP type and Temperature timeseries.<br />
| **h**: h-Wert (h-value) , depending on SLP type and daily mean temperature.<br />
| **F**: Wochentagsfaktor (week day factor), depending on SLP type and day of the week.<br />
| **T**: Daily mean temperature 2 meters above the ground (simple mean or "geometric series", which means a weighted sum over the previous days).<br />
| **SF**: Stundenfaktor (hour factor)<br />

The geometric series approach is meant to account for thermal inertia.

$$ \theta = \frac{T_t + 0.5 \cdot T_{t-1} + 0.25 \cdot T_{t-2} + 0.125 \cdot T_{t-3}}{1 + 0.5 + 0.25 + 0.125} $$

Depending on the profile type, different coefficients A, B, C, D for the sigmoid function are used.

$$ h(\theta) =\frac{A}{1+(\frac{B}{\theta-\theta_0})^C} + D  $$

$$ \theta_0 = 40^\circ C $$

Types of houses:

| **EFH**: Single family house<br />
| **MFH**: Multi family house<br />
| **GMK**: Meetal and automotive<br />
| **GHA**: Retail and wholesale<br />
| **GKO**: Local authorities, credit institutions and insurance companies<br />
| **GBD**: Other operational services<br />
| **GGA**: Restaurants<br />
| **GBH**: Accommodation<br />
| **GWA**: Llaundries, dry cleaning<br />
| **GGB**: Horticulture<br />
| **GBA**: Bakery<br />
| **GPD**: Paper and printing<br />
| **GMF**: Household-like business enterprises<br />
| **GHD**: Total load profile Business/Commerce/Services<br />

Building class:

The parameter ``building_class`` (German: Baualtersklasse) can assume values in the range 1-11.


The electrical profiles are the standard load profiles from BDEW. All profiles
have a resolution of 15 minutes. They are based on measurements in the German
electricity sector. There is a dynamic function (h0_dyn) for the houshold (h0)
profile that better takes the seasonal variance into account.

$$ F_t = -3,92\cdot10^{-10} \cdot t^4 + 3,2\cdot10^{-7} \cdot t^3– 7,02\cdot10^{-5}\cdot t^2 + 2,1\cdot10^{-3}\cdot t + 1,24 $$

With `t` the day of the year as a decimal number.

The following profile types are available.
Be aware that the types in Python code are strings in **lowercase**.

| **G0**:, "General trade/business/commerce", "Weighted average of profiles G1-G6"<br />
| **G1**:, "Business on weekdays 8 a.m. - 6 p.m.", "e.g. offices, doctors' surgeries, workshops, administrative facilities"<br />
| **G2**:, "Businesses with heavy to predominant consumption in the evening hours", "e.g. sports clubs, fitness studios, evening restaurants"<br />
| **G3**:, "Continuous business", "e.g. cold stores, pumps, sewage treatment plants"<br />
| **G4**:, "Shop/barber shop"<br />
| **G5**:, "Bakery with bakery"<br />
| **G6**:, "Weekend operation", "e.g. cinemas"<br />
| **G7**:, "Mobile phone transmitter station", "continuous band load profile"<br />
| **L0**:, "General farms", "Weighted average of profiles L1 and L2"<br />
| **L1**:, "Farms with dairy farming/part-time livestock farming",<br />
| **L2**:, "Other farms",<br />
| **H0/H0_dyn**:, "Household/dynamic houshold",<br />


## Installation

1. Create and activate enviroment. Example with anaconda:   `conda activate lesbdew`
2. cd to folder with github clone
3. `pip install -e .`

## Usage

1. `cd "folder/main.py"`
2. Store necessary GIS data to "folder/data/raw" and modify `overwrite_shp.py` accordingly to adapt the columns of the shapefile
3. Prepare shp.-file with prepare_for_bdew.py: this scripts adapts the shapefile using the functions in datamgmt to assign building age, building type etc.
3. `python main.py`
4. Results will be stored in "results".

### Census file format
Needs a csv file that links the GITTER_ID_ item to the census statistics. For an example of the file, see ./data/census/2024-08-12_zensus.csv.

### Shapefile input format
Needs to be a shapefile with columns:
['GML_ID', 'USE_CALC', 'AREA_CALC', 'VOL_CALC', 'HEIGH_MEAS', 'HEIGH_CALC', 'CONSTRUCTI', 'CENS_GRID', 'geometry']
If not, change with the script in ./data/raw-data/overwrite_shp.py.

## Support

- Post an issue
- Contact the authors

## Contributing

- Open a detailed pull request and email the authors.

## Authors and acknowledgment

- Lennart Trentmann (lennart.trentmann@tum.de)
- Amedeo Ceruti (amedeo.ceruti@tum.de)
- Benedikt Schweiger (benedikt.schweiger@tum.de)

Acknowledgement: the Heat2Q project partners for their ongoing feedback.

## Project status

In development until early 2026.
