"""
@author: Lennart Trentmann (lennart.trentmann@tum.de)
         Amedeo Ceruti (amedeo.ceruti@tum.de)

Constants & parameters used throughout the datamanagement functions.
"""

from datetime import date
import collections
import string
import csv
import pandas as pd

EPSG = 25832  # 5243 or 25832 or 4326 # Coordinate reference system


class Parameters:
    """
    Class containing the main parameters for BDEW, census, and typology processing.
    """

    def __init__(self, census_path=None, iwu_path=None):
        self.bdew = {
            # Height of a given floor (BDEW = 3, TABULA = 2.5 m, EnEV = 3.125 m)
            'HEIGHT_FLOOR': 3.125,
            'HEIGHT_CELLAR': 0,  # Height of the cellar
            'FLOORS_CELLAR': 0,  # Number of cellar floors
            'EPSG': EPSG,        # Geographic positioning system
            'RUNID': str(date.today()),  # ID to tag all output files
        }

        self.zensus = {
            'RUNID': str(date.today()),  # ID to tag all output files
            'EPSG': EPSG,
            'HEIGHT_SURR_FILTER': 3.5,  # Filter out buildings shorter than surroundings (m)
            'AREA_FILTER': 0,            # Filter out buildings smaller than this area (m²)
            'VOLUME_FILTER': 250,        # Filter out buildings smaller than this volume (m³)
            # Probability of a building being in a given TABULA age category
            'p_age-residential': collections.OrderedDict([
                ('A', 0.082), ('B', 0.075),
                ('C', 0.288 / 3), ('D', 0.288 / 3), ('E', 0.288 / 3),
                ('F', 0.309 / 3), ('G', 0.309 / 3), ('H', 0.309 / 3),
                ('I', 0.152), ('J', 0.095 / 2), ('K', 0.095 / 2), ('L', 0),
            ]),
            'p_age-nonresidential': collections.OrderedDict([
                ('A', 0.466), ('B', 0.439), ('C', 0.095)
            ]),
            'netto_area_factor-residential': 0.84,
            'netto_area_factor-nonresidential': 0.84,
            'age_mapping-nonres': {
                'A': 'A', 'B': 'A', 'C': 'A', 'D': 'A', 'E': 'A',
                'F': 'A', 'G': 'B', 'H': 'B', 'I': 'B', 'J': 'B',
                'K': 'C', 'L': 'C',
            },
        }

        self.typology = {
            'tabula_ages': (
                ('A', 1859), ('B', 1860), ('C', 1919), ('D', 1949),
                ('E', 1958), ('F', 1969), ('G', 1979), ('H', 1984),
                ('I', 1995), ('J', 2002), ('K', 2010), ('L', 2016),
            ),
            'iwu_ages': (
                ('A', 1978), ('B', 1979), ('C', 2010),
            ),
            'use_types': {
                'SFH': ['SINGLE_RES'],
                'TH': ['SINGLE_RES'],
                'AB': ['MULTI_RES'],
                'MFH': ['MULTI_RES'],
                'NWG_1': ['OFFICE'],
                'NWG_2': ['UNIVERSITY'],
                'NWG_3': ['HOSPITAL'],
                'NWG_7': ['RESTAURANT'],
                'NWG_G1': ['OFFICE', 'RETAIL'],
            }
        }

        def load_csv(filename, value_type=float):
            with open(f'databases/{filename}', mode='r') as f:
                reader = csv.reader(f, delimiter=';')
                return {row[0]: value_type(row[1]) for row in reader}

        self.spez_hot_water_mapping = load_csv('spez_hot_water_mapping.csv', float)
        self.alpha_mapping = load_csv('alpha_mapping.csv', float)
        self.bdew_mapping = load_csv('bdew_mapping.csv', str)
        self.bdew_elec_mapping = load_csv('bdew_elec_mapping.csv', str)

        # Load CSV files as DataFrames
        self.spez_heat_bj = pd.read_csv('databases/spez_heat_bj.csv', sep=';', encoding="ISO-8859-1", index_col=0)
        self.spez_elec_type = pd.read_csv('databases/spez_elec.csv', sep=';', encoding="ISO-8859-1", index_col=0)
        self.building_class_mapping = pd.read_csv('databases/building_class_mapping.csv', sep=';', encoding="ISO-8859-1", index_col=0)

        if census_path is not None:
            self.set_p_age(census_path)
            self.set_p_age_iwu(census_path)

        if iwu_path is not None:
            self.set_iwu_use_type(iwu_path)

    def set_p_age(self, census_path):
        """
        Sets the p_age-residential parameter from census data.

        :param census_path: Path to census CSV file.
        :return: Updated p_age-residential dictionary.
        """
        df = pd.read_csv(census_path, sep=",", header=0, index_col=0)
        self.zensus['p_age-residential'] = (df.iloc[:, 0] / df.iloc[:, 0].sum()).to_dict()
        return self.zensus['p_age-residential']

    def set_p_age_iwu(self, census_path):
        """
        Sets the p_age-nonresidential parameter from census data.

        :param census_path: Path to census CSV file.
        :return: Updated p_age-nonresidential dictionary.
        """
        df = pd.read_csv(census_path, sep=",", header=0, index_col=0)
        total = df.sum().values[0]

        self.zensus['p_age-nonresidential']['A'] = df.loc[list(string.ascii_uppercase[:6]), :].sum().values[0] / total
        self.zensus['p_age-nonresidential']['B'] = df.loc[list(string.ascii_uppercase[6:10]), :].sum().values[0] / total
        self.zensus['p_age-nonresidential']['C'] = df.loc[['K', 'L'], :].sum().values[0] / total

        return self.zensus['p_age-nonresidential']

    def set_iwu_use_type(self, iwu_path):
        """
        Sets the use_types parameter from IWU building types.

        :param iwu_path: Path to IWU mapping CSV file.
        :return: Updated use_types dictionary.
        """
        df = pd.read_csv(iwu_path, sep=";", header=0, index_col=0)
        dftype = df.set_index("iwu mapping")[["use_type_1", "use_type_2", "use_type_3"]]
        dftype = dftype.dropna(how='all')              # drop rows where all are NaN
        dftype2 = dftype[~dftype.duplicated(keep='first')]  # drop duplicates

        if len(dftype2) != len(dftype.index.unique()):
            raise ValueError('Duplicate entries in IWU mapping file for use types.')

        # Convert to dict with variable-length lists per key
        d = {key: [i for i in row.values if isinstance(i, str)] for key, row in dftype2.iterrows()}

        # Update typology use_types without deleting initialized ones
        self.typology['use_types'].update(d)

        return self.typology['use_types']
