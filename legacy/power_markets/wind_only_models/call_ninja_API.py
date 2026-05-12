import os
import json

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

CU_token = os.environ["NINJA_CU_TOKEN"]
WPI_token = os.environ["NINJA_WPI_TOKEN"]
myToken = os.environ["NINJA_MY_TOKEN"]
api_base = 'https://www.renewables.ninja/api/'

s = requests.session()
s.headers = {'Authorization': 'Token ' + WPI_token}
url = api_base + 'data/wind'

def get_args(time, lat, lon):
    if time == 2030:
        args_2030 = {
            'lat': lat,
            'lon': lon,
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'capacity': 1.0,
            'height': 120,
            'turbine': 'Gamesa G128 5000',
            'format': 'json'
        }
        return args_2030
    elif time == 2023:
        args_2023 = {
            'lat': lat,
            'lon': lon,
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'capacity': 1.0,
            'height': 90.2,
            'turbine': 'Bonus B82 2300',
            'format': 'json'
        }
        return args_2023

data = pd.read_excel(r"C:\Users\eduar\OneDrive\Desktop\PycharmProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\power_markets\state_level_datasets\AP_location_dataset.xlsx", sheet_name='US AP Plants')

#Eliminate the first 4 columns of the dataframe and rename the next first column to "Company"
data = data.iloc[:, 4:]
  
# Rename the next first column to "Company"
data.rename(columns={data.columns[0]: "Company"}, inplace=True)

"""
API CALL 

r = s.get(url, params=args)

parsed_response = json.loads(r.text)
data = pd.read_json(json.dumps(parsed_response['data']), orient='index')
metadata = parsed_response['metadata']
"""

def API_call(params, time, state, town, url=url):
    r = s.get(url, params=params)
    parsed_response = json.loads(r.text)
    data_cf = pd.read_json(json.dumps(parsed_response['data']), orient='index')
    metadata = parsed_response['metadata']
    data_cf.to_json(f'Wind data/more capacity data/data/{time}_{town}_{state}_wind_capacity_data.json')
    # metadata.to_json( f'power_markets/state_level_datasets/metadata/{time}_{town}_{state}_wind_capacity_metadata.json')

# iterate through rows in data dataframe, get lat and lon for each row, and call get_args function
# then call the API
times = [2023, 2030]
for time in times:
    for index, row in data.iterrows():
        if index >= 0 and time == 2030:
            lat = row['lat']
            lon = row['lon']
            town = row['City']
            state = row['State']
            args = get_args(time, lat, lon)
            response = API_call(args, time, state, town)

