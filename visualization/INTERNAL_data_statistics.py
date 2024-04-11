import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import pprint
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_excel_sheets(file_path):
    # Load the Excel file
    xls = pd.ExcelFile(file_path)

    # Dictionary to store the DataFrames for each sheet
    dataframes = {}

    # Iterate over each sheet in the Excel file
    for sheet_name in xls.sheet_names:
        # Read the sheet into a DataFrame
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # Store the DataFrame in the dictionary
        dataframes[sheet_name] = df

    return dataframes


ROOT_FILES = r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model"
root_path = rf'{ROOT_FILES}\v14_DATASET'
matchings = ['yearly', 'monthly', 'hourly']
CBAM = ['', '_CBAM']
times = [2023, 2030]
scenarios = ['B', 'C', 'D']
technologies = ['AP_SMR', 'AP_CCS', 'AP_BH2S', 'AP_AEC']
CI_technologies = ['AP SMR', 'AP CCS', 'AP BH2S', 'AP AEC']
metrics = ['_NPV', '_CAC', '_Potential', '_CE', '_CAPEX', '_OPEX', '_support_45V', '_support_45Q', '_support_45Y',
           '_support_48E']


datafiles = {}

for matching in matchings:
    for C in CBAM:
        temp = C if matching == 'monthly' else ''
        baselineData = load_excel_sheets(root_path + temp + '_' + matching + '.xlsx')
        datafiles[matching + temp] = baselineData

# Clean the data into scenarios and timeframe
cleaned_datafiles_with_matching = {time: {} for time in times}

#Manually get CI Files
CI_data = {
    'AP CCS': datafiles[list(datafiles.keys())[0]]['CI_AP CCS'],
    'AP BH2S': datafiles[list(datafiles.keys())[0]]['CI_AP BH2S'],
    'AP AEC': datafiles[list(datafiles.keys())[0]]['CI_AP AEC'],
    'AP SMR': datafiles[list(datafiles.keys())[0]]['CI_AP SMR']
}

# Process each file and clean the data with additional checks for columns
for key, file_data in datafiles.items():
    for sheet_name, df in file_data.items():
        matching_type = key.split("_")[-1]  # Extract the matching type from the key

        # Check if the sheet name contains "CI_"
        if sheet_name.startswith("CI_"):
            # Determine the technology based on the sheet name
            technology = sheet_name.replace("CI_", "").replace(" ", "_")

            # For each time in the dataframe
            for time in df['time'].unique():
                if matching_type not in cleaned_datafiles_with_matching[time]:
                    cleaned_datafiles_with_matching[time][matching_type] = {}
                if "CI" not in cleaned_datafiles_with_matching[time][matching_type]:
                    cleaned_datafiles_with_matching[time][matching_type]["CI"] = {}
                cleaned_datafiles_with_matching[time][matching_type]["CI"][technology] = df[df['time'] == time].copy()

        elif 'time' in df.columns and 'scenario' in df.columns:  # Check if the columns exist before grouping
            # Group by time and scenario
            grouped = df.groupby(['time', 'scenario'])

            for (time, scenario), group_df in grouped:
                if matching_type not in cleaned_datafiles_with_matching[time]:
                    cleaned_datafiles_with_matching[time][matching_type] = {}
                if scenario not in cleaned_datafiles_with_matching[time][matching_type]:
                    cleaned_datafiles_with_matching[time][matching_type][scenario] = {}
                cleaned_datafiles_with_matching[time][matching_type][scenario][sheet_name] = group_df.copy()

for time_key, matching_data in cleaned_datafiles_with_matching.items():
    for matching_type, scenario_data in matching_data.items():
        if "CI" in scenario_data:
            CI_data = scenario_data["CI"]
            for tech, tech_df in CI_data.items():
                grouped = tech_df.groupby(['time', 'scenario'])
                for (time, scenario), group_df in grouped:
                    if scenario not in scenario_data:
                        scenario_data[scenario] = {}
                    if f"CI_{tech}" not in scenario_data[scenario]:
                        scenario_data[scenario][f"CI_{tech}"] = {}
                    scenario_data[scenario][f"CI_{tech}"] = group_df.copy()
            del scenario_data["CI"]  # Remove the original ungrouped CI data

def aggregate_lists(series):
    flattened_list = [item for sublist in series for item in sublist]
    return {
        'median': np.median(flattened_list),
        'q25': np.percentile(flattened_list, 25),
        'q75': np.percentile(flattened_list, 75),
        'min': min(flattened_list),
        'max': max(flattened_list)
    }

all_frames_to_combine = {}

for time in times:
    for matching in cleaned_datafiles_with_matching[time]:
        for scenario in scenarios:
            for key, metric in cleaned_datafiles_with_matching[time][matching][scenario].items():
                all_frames_to_combine[key] = [] if key not in all_frames_to_combine else all_frames_to_combine[key]

                logging.info(f"Added entry {key} to all_frames_dictionary")

                metric = metric.describe()
                logging.info(f"Columns: {metric.columns} and {metric.index}")
                if 'simulation' in metric.columns:
                    metric.drop(['time','simulation'],inplace=True, axis=1)
                elif 'sim' in metric.columns:
                    metric.drop(['time', 'sim'], inplace=True, axis=1)
                elif 'Simulation' in metric.columns:
                    metric.drop(['time', 'Simulation'], inplace=True, axis=1)

                metric.insert(0, 'statistic', metric.index)
                metric.insert(0, 'matching', matching)
                metric.insert(0, 'time', time)
                metric.insert(0, 'scenario', scenario)

                logging.info(f"Succesfully labeled column with matching: {matching}")

                all_frames_to_combine[key].append(metric)
                logging.info(f"Successfully appended statistics to dict")


for key in all_frames_to_combine.keys():
    all_frames_to_combine[key] = pd.concat(all_frames_to_combine[key],axis=0)

logging.info("Succesfully concateinated all data into the metrics")

def dataframes_to_excel(dfs, file_name):
    """
    Convert multiple pandas DataFrames into one Excel file with multiple sheets.

    Parameters:
    dfs (dict): Dictionary where keys are sheet names and values are corresponding DataFrames
    file_name (str): Name of the Excel file

    Returns:
    None
    """
    try:
        with pd.ExcelWriter(file_name) as writer:
            for sheet_name, df in dfs.items():
                if isinstance(df, dict):  # check if value is another dict (specifically for 'CI')
                    for sub_sheet_name, sub_df in df.items():
                        # use a combination of main key and sub key as the sheet name
                        sub_sheet_name = f"{sheet_name}_{sub_sheet_name}"
                        sub_df.to_excel(writer, sheet_name=sub_sheet_name, index=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f'Successfully written to {file_name}')
    except Exception as e:
        print(f'An error occurred: {e}')

dataframes_to_excel(all_frames_to_combine, f'{ROOT_FILES}/visuals/AP_NE_Statistics.xlsx')


