# Defining the function to perform all the required operations
import pandas as pd
from ast import literal_eval


file_path = r'C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\v14_DATASET_monthly.xlsx'
# output_file_path = r"FINAL final figures/tables/CAPEX_average_v8.xlsx"
# output_path = 'FINAL final figures/tables/CAPEX_component_tables_updated_v8.xlsx'
# roi_output_path = 'FINAL final figures/tables/roi_table_v8.xlsx'
support_output_path = r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\visuals\tables.xlsx"

def process_capex_data(file_path, sheet_name, output_path):
    # Read the data from the specified sheet
    capex_component_data = pd.read_excel(file_path, sheet_name=sheet_name)

    # Function to calculate the mean of dictionary values across the group
    def calculate_mean(dictionary_list):
        sum_dict = {key: 0 for key in dictionary_list[0].keys()}
        for dictionary in dictionary_list:
            for key, value in dictionary.items():
                sum_dict[key] += value
        mean_dict = {key: value / len(dictionary_list) for key, value in sum_dict.items()}
        return mean_dict

    def apply_mean(group):
        columns_with_dict = ['AP_SMR_NPV', 'AP_CCS_NPV', 'AP_BH2S_NPV', 'AP_AEC_NPV']
        for col in columns_with_dict:
            group[col] = group[col].apply(literal_eval)
        mean_values = {col: calculate_mean(group[col].tolist()) for col in columns_with_dict}
        return pd.Series(mean_values)

    grouped_data = capex_component_data.groupby(['time', 'scenario']).apply(apply_mean).reset_index()

    # Define the order of rows and mapping for row names
    rows_order = [
        'UC', 'installation', 'instrumentation_and_controls', 'piping', 'electrical',
        'building_process_auxiliary', 'service_facilities_and_yard_improvements', 'land', 'engineering_supervision',
        'legal_expenses', 'construction_expense_and_contractors_fee', 'contingency', 'FCI', 'WC', 'CAPEX'
    ]

    row_name_mapping = {
        'UC': 'Purchased Equipment Cost',
        'installation': 'Installation',
        'instrumentation_and_controls': 'Instrumentation And Controls',
        'piping': 'Piping',
        'electrical': 'Electrical',
        'building_process_auxiliary': 'Building Process Auxiliary',
        'service_facilities_and_yard_improvements': 'Service Facilities And Yard Improvements',
        'land': 'Land',
        'engineering_supervision': 'Engineering Supervision',
        'legal_expenses': 'Legal Expenses',
        'construction_expense_and_contractors_fee': 'Construction Expense And Contractors Fee',
        'contingency': 'Contingency',
        'FCI': 'Fixed Capital Investment',
        'WC': 'Working Capital',
        'CAPEX': 'Total Capital Investment'
    }

    # Define the columns mapping
    columns_mapping = {
        'AP_SMR_NPV': 'AP',
        'AP_CCS_NPV': 'AP CCS',
        'AP_BH2S_NPV': 'AP BH2S',
        'AP_AEC_NPV': 'AP AEC'
    }

    # Function to create a table for a specific group
    def create_table(group):
        table_data = {col_name: [group[col][key if key not in ['FCI', 'WC', 'UC'] else key] for key in rows_order] for col, col_name in columns_mapping.items()}
        table_df = pd.DataFrame(table_data, index=[row_name_mapping[row] for row in rows_order])
        return table_df

    tables = {}
    for index, row in grouped_data.iterrows():
        time, scenario = row['time'], row['scenario']
        tables[(time, scenario)] = create_table(row)

    # Save the tables to Excel file
    with pd.ExcelWriter(output_path) as writer:
        for (time, scenario), table in tables.items():
            sheet_name = f"Time_{time}_Scenario_{scenario}"
            table.to_excel(writer, sheet_name=sheet_name)

# Usage example with the provided file and sheet

sheet_name = 'CAPEX_component'
output_path = r"C:\Users\eduar\OneDrive\Desktop\PythonProjects\Ammonia Project\pythonProject1\NOVEMBER AP Model\visuals\tables.xlsx"#
process_capex_data(file_path, sheet_name, output_path)


def process_roi_data(file_path, sheet_name, output_path):
    # Read the data from the specified sheet
    roi_data = pd.read_excel(file_path, sheet_name=sheet_name)

    # Group by 'time' and 'scenario' and calculate the mean for ROI columns
    mean_roi_data = roi_data.groupby(['time', 'scenario']).mean().reset_index().drop(columns=['simulation'])

    # Save the table to an Excel file
    mean_roi_data.to_excel(output_path, index=False)

    return mean_roi_data

# Usage example with the provided file and sheet
#
# roi_sheet_name = 'ROI'
# roi_table = process_roi_data(file_path, roi_sheet_name, roi_output_path)

support_sheet_name = 'absolute_support'

support_table = process_roi_data(file_path, support_sheet_name, support_output_path)

# process_roi_data('NPV_only_sensitivity.xlsx', 'NPV', 'average_NPV.xlsx')

def mean_capex(file_path, capex_columns, output_file_path, sheet_name = 'CAPEX_OPEX'):
    # Read the data from the Excel file
    data = pd.read_excel(file_path, sheet_name=sheet_name)

    # Group by 'time' and 'scenario', and calculate the mean for the specified CAPEX columns
    mean_values = data.groupby(['time', 'scenario'])[capex_columns].mean().reset_index()

    # Write the result to an Excel file
    mean_values.to_excel(output_file_path, index=False)
    print(f"Mean CAPEX values have been written to {output_file_path}")


# Example usage
capex_columns = ["AP_SMR_CAPEX", "AP_CCS_CAPEX", "AP_BH2S_CAPEX", "AP_AEC_CAPEX"]  # Replace with your CAPEX columns


# mean_capex(file_path, capex_columns, output_file_path)
#
# mean_capex(file_path, ["AP_SMR_NPV", "AP_CCS_NPV", "AP_BH2S_NPV", "AP_AEC_NPV"], "tables/NPV_mean.xlsx",
#            sheet_name='NPV')