from pathlib import Path
import pandas as pd
import os


def process_and_aggregate_dataset(dataset_path):
    # Read the dataset
    data = pd.read_excel(dataset_path)

    # Drop the 'simulation' column
    data = data.drop("simulation", axis=1)

    # Group by 'time' and 'scenario' and perform aggregation
    data = data.groupby(['time', 'scenario']).agg(
        ['max', 'min', ('P5', lambda x: x.quantile(0.05)), ('P95', lambda x: x.quantile(0.95)), 'mean', 'median']).reset_index()

    # Drop scenario 'A'
    data = data[data['scenario'] != 'A']

    # Rename scenarios 'B', 'C', 'D' to 'A', 'B', 'C'
    scenario_mapping = {'B': 'A', 'C': 'B', 'D': 'C'}
    data['scenario'] = data['scenario'].map(scenario_mapping)

    # Set 'time' and 'scenario' as index again
    data.set_index(['time', 'scenario'], inplace=True)

    return data


def combine_and_export_datasets(dataset_paths, export_path):
    combined_data = pd.DataFrame()

    for path in dataset_paths:
        processed_data = process_and_aggregate_dataset(path)
        combined_data = pd.concat([combined_data, processed_data])

    # Export the combined DataFrame to CSV
    combined_data.to_csv(export_path)


dataset_paths = [r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_hourly_500.xlsx"
    , r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_hourly_1000.xlsx",
                 r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_hourly_2000.xlsx",
                 r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_hourly.xlsx",
                 r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_hourly_10000.xlsx"]


export_path = r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\convergence analysis\combined_dataset.csv"
combine_and_export_datasets(dataset_paths, export_path)
