import json
import os

import pandas as pd

root_dir = "capacity_factors"  # Adjust to your directory path
data_2023 = {}
data_2030 = {}

# Walk through the directory and subdirectories
for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".json"):
            year, town, state, gen_type, _, _ = filename.split("_")
            label = f"{town}_{state}_{gen_type}"
            filepath = os.path.join(dirpath, filename)

            # Load JSON data
            with open(filepath, "r") as file:
                data = json.load(file)

            # Aggregate data by year
            if year == "2023":
                data_2023[label] = list(data["electricity"].values())
            elif year == "2030":
                data_2030[label] = list(data["electricity"].values())


# Function to convert data to DataFrame and transpose
def process_data(data):
    df = pd.DataFrame(data)
    df = df  # Transpose
    return df


# Convert to DataFrame and Transpose
df_2023 = process_data(data_2023)
df_2030 = process_data(data_2030)

# Save to Excel
with pd.ExcelWriter("QA files/combined_capacity_factors_transposed.xlsx") as writer:
    df_2023.to_excel(writer, sheet_name="2023")
    df_2030.to_excel(writer, sheet_name="2030")

print(
    "Excel file 'combined_capacity_factors_transposed.xlsx' created with sheets for 2023 and 2030."
)
