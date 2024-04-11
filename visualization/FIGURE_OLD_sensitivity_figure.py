import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
file_directory = "alldata_v6.xlsx"
# Read the NPV and sensitivity sheets
npv_sheet = pd.read_excel(file_directory, sheet_name="NPV")
sensitivity_sheet = pd.read_excel(file_directory, sheet_name="sensitivity")

# Merge the two sheets
merged_data = pd.merge(
    npv_sheet,
    sensitivity_sheet,
    left_on=['time', 'scenario', 'simulation'],
    right_on=['Time', 'Scenario', 'Simulation'],
    how='inner'
)

# Define the NPV columns and independent columns
npv_columns = ['AP_SMR_NPV', 'AP_CCS_NPV', 'AP_BH2S_NPV', 'AP_AEC_NPV']
independent_columns = sensitivity_sheet.columns.difference(['Time', 'Scenario', 'Simulation'])

# Function to create a comprehensive table for correlation coefficients with all independent variables
def create_full_correlation_table(data):
    correlation_table_full = data.groupby(['time', 'scenario']).apply(
        lambda x: x[npv_columns + list(sensitivity_sheet.columns.difference(['Time', 'Scenario', 'Simulation']))].corr().loc[npv_columns]
    ).reset_index()
    return correlation_table_full

# Create the full correlation table for all independent variables
full_correlation_table = create_full_correlation_table(merged_data)

# Rename the column where the NPV is specified to "NPV"
full_correlation_table.rename(columns={'level_2': 'NPV'}, inplace=True)

# Mapping the NPV column names to the new names
npv_name_mapping = {
    'AP_SMR_NPV': 'AP SMR',
    'AP_CCS_NPV': 'AP CCS',
    'AP_BH2S_NPV': 'AP BH2S',
    'AP_AEC_NPV': 'AP AEC'
}

# Rename the actual columns corresponding to the NPV variables
full_correlation_table.rename(columns=npv_name_mapping, inplace=True)

# Save the updated correlation table as a CSV file
final_csv_file_path = "sensitivity/correlation_{}.csv".format("CBAM" if 'CBAM' in file_directory else "")
full_correlation_table.to_csv(final_csv_file_path, index=False)