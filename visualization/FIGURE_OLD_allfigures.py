#!/usr/bin/env python
# coding: utf-8

# In[12]:

import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import ast
# from PPA_models import LCOE_dataset

# PPA_data = LCOE_dataset
year = 2023
matching = 'monthly'
CBAM = False

print('running', year, matching, CBAM)
if matching == 'monthly':
    NPV_low = -800
elif matching == 'hourly':
    NPV_low = -2000
else:
    NPV_low = -400
# Specify the path to your Excel file
# excel_file_path = f"{year}_v8{'_CBAM' if CBAM else ''}{'_'+matching}.xlsx"
all_data_file_path = f"TC_FINAL_alldata_v12{'_CBAM' if CBAM else ''}{'_'+matching}.xlsx"
figure_ending_name = f"TC_FINAL_alldata_v12{'_CBAM' if CBAM else ''}{'_'+matching}" #"default" is the base case
# time_varying_filepath = r"2023 US Data AP renewE0 TIME VARYING CI Python.xlsx"

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

# allData = load_excel_sheets(excel_file_path)

def clean_and_prepare_data(filepath, sheet_names, technologies):
    """
    This function reads an Excel file, renames columns, sets multi-index, and returns a dictionary of prepared dataframes.
    
    Parameters:
    filepath (str): The file path of the Excel file.
    sheet_names (list): A list of sheet names to be read.
    technologies (list): A list of technologies to be used in the multi-index.

    Returns:
    A dictionary of prepared dataframes.
    """
    # Load the sheets
    sheets = pd.read_excel(filepath, sheet_name=sheet_names)

    # Function to convert column name to integer if it's a year
    def convert_column_name(name):
        if "_" in name:  # Check if the column name starts with '_'
            try:
                return int(name[1:])  # Remove '_' and convert to integer
            except ValueError:  # If conversion to integer fails, return the original name
                return name
        else:
            return name

    # Rename columns and set index for each sheet
    for name in sheet_names:
        sheets[name].columns = [convert_column_name(col) for col in sheets[name].columns]
        sheets[name].set_index('Index', inplace=True)

    # Create a multi-index by repeating the list of technologies the appropriate number of times
    tech_index = pd.MultiIndex.from_product([technologies, range(0, 50)], names=['Technology', 'Index'])

    # Assign the multi-index to the DataFrames
    for name in sheet_names:
        sheets[name].index = tech_index

    return sheets

columns = ['AP_CCS_NPV', 'AP_BH2S_NPV', 'AP_AEC_NPV']
def compare_policy_scenarios_subplot(with_policy_df, no_policy_df, column_names, reference, ax, title, show_legend, bottom, left):
    """
    Function to compare the policy scenarios and plot them.
    """
    # Create a copy of the dataframes to avoid the SettingWithCopyWarning
    no_policy_df = no_policy_df.copy()
    with_policy_df = with_policy_df.copy()
    
    # Add a 'Scenario' column to each DataFrame
    no_policy_df['Scenario'] = 'No Policy'
    with_policy_df['Scenario'] = 'IRA'
    
    # Add legend only if show_legend is True
    if show_legend:
        legend = ax.legend(facecolor='white', edgecolor='black', bbox_to_anchor=(1, 0.8))
        legend.get_frame().set_linewidth(0)
    
    # Calculate the quartiles and Interquartile Range (IQR)
    q1 = reference.quantile(0.25)
    q2 = reference.quantile(0.5)
    q3 = reference.quantile(0.75)
    iqr = q3-q1
    q0 = q1-1.5*iqr
    q5 = q3+1.5*iqr
    
    # Add a 'Scenario' column to each DataFrame
    no_policy_df['Scenario'] = 'No Policy'
    with_policy_df['Scenario'] = 'IRA'
    
    # Combine the two DataFrames
    combined_df = pd.concat([no_policy_df, with_policy_df])
    
    # Melt the dataframe to long format
    melted_df = pd.melt(combined_df, id_vars='Scenario', value_vars=column_names,
                        var_name='Column', value_name='Value')
    
    # Create the boxplot
    boxplot = sns.boxplot(data=melted_df, x='Column', y='Value', hue='Scenario', palette=('gray','pink'), showfliers=False, width=0.5, ax=ax)
        
    ax.get_legend().remove()
        
    # Set labels and title
    if not left:
        ax.set_ylabel(r'')
    else:
        ax.set_ylabel(r'NPV [$\frac{2023\$}{Tonne \ NH_3}$]', fontweight='bold')
        
    ax.set_xlabel('')
    
    # Add horizontal lines for quartiles
    ax.axhline(y=q1, color='gray', linestyle='--', linewidth=2, alpha=0.25)
    ax.axhline(y=q2, color='gray', linestyle='--', linewidth=2, alpha=0.25)
    ax.axhline(y=q3, color='gray', linestyle='--', linewidth=2, alpha=0.25)
    ax.axhline(y=q0, color='gray', linestyle='--', linewidth=2, alpha=0.25)
    ax.axhline(y=q5, color='gray', linestyle='--', linewidth=2, alpha=0.25)
    
    # Add filled areas between quartiles
    x = np.linspace(ax.get_xlim()[0], ax.get_xlim()[1], 100)
    y1 = np.full_like(x, q2)
    y2 = np.full_like(x, q3)
    ax.fill_between(x, y1, y2, color='gray', alpha=0.1, edgecolor='black', hatch='////')
    y1 = np.full_like(x, q1)
    ax.fill_between(x, y1, y2, color='gray', alpha=0.1, edgecolor='black', hatch='////')
    
    # Rotate x-axis labels if needed
    if not bottom:
        ax.set_xticklabels(['','',''])
    else:
        ax.set_xticklabels([ 'AP CCS', 'AP BH2S', 'AP AEC'], fontweight='bold', rotation=45)
        
    
    # Add annotation
    ax.annotate('AP SMR', xy=(0.5, 3), xytext=(-.5*0.95, 1.05*q5), color='gray')
    # ax.grid(axis='y', color='black', alpha=0.5, linestyle='dotted')
    ax.set_title(title, fontweight ='bold')
    # ax.minorticks_on()
    # ax.tick_params(axis='x', which='both', bottom=False, top=False)

    if show_legend:
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles=handles[0:], labels=labels[0:], loc='lower left', facecolor='white', edgecolor='black')
        # ax.legend_.set_bbox_to_anchor((3.88,0.53))
    
    ax.set_ylim(-800,275)
    ax.set_xlim(-0.5,2.5)
    # ax.yaxis.set_label_coords(-0.1, 0.5)  

technologies = ['AP', 'AP_CCS', 'AP_BH2S', 'AP_AEC']
from matplotlib.patches import Patch

def plot_stacked_bar_subplot(data, technologies, ax, show_legend, bottom, left, isGrid=False):
    # Define helper function to calculate error ranges
    def ranges(dataframe):
        mean = dataframe.mean()
        lower = mean - dataframe.min()
        upper = dataframe.max() - mean
        return [[lower], [upper]]

    # Define parameters for the plot
    width = 0.2
    shift = 0.2

    # Define color and label for each CI subcategory
    ci_subcategories = ['SMR', 'Electricity LCA', 'NG LCA', 'Biomass LCA']
    colors = ['gray', '#ff7f00', '#4daf4a', '#a65628']  # Set color palette to closely match the reference image

    # Iterate over the different technologies
    for i, tech in enumerate(technologies):
        # Define data
        y1 = data[f'{tech}_STACK_CI'] if f'{tech}_STACK_CI' in data.columns else np.zeros(len(data))
        y2 = data[f'{tech}_NG_CI'] if f'{tech}_NG_CI' in data.columns else np.zeros(len(data))
        y3 = data[f'{tech}_BIO_CI'] if f'{tech}_BIO_CI' in data.columns else np.zeros(len(data))
        y4 = data[f'{tech}_E_CI_2026'] if f'{tech}_E_CI_2026' in data.columns else np.zeros(len(data))

        # Calculate means
        y1_mean = y1.mean()
        y2_mean = y2.mean()
        y3_mean = y3.mean()
        y4_mean = y4.mean()

        # Calculate error ranges
        y1_err = ranges(y1)
        y2_err = ranges(y2)
        y3_err = ranges(y3)
        y4_err = ranges(y4)

        # Create stacked bar plots with a shift depending on the technology
        ax.bar(i, y1_mean, color=colors[0], width=width, edgecolor='black', yerr=y1_err, capsize=4)
        ax.bar(i+shift, y4_mean, bottom=y1_mean, color=colors[1], width=width, edgecolor='black', yerr=y4_err, capsize=4)
        ax.bar(i+shift*2, y2_mean, bottom=y1_mean+y4_mean, color=colors[2], width=width, edgecolor='black', yerr=y2_err, capsize=4)
        ax.bar(i+shift*3, y3_mean, bottom=y1_mean+y2_mean+y4_mean, color=colors[3], width=width, edgecolor='black', yerr=y3_err, capsize=4)

    # Set x ticks and labels
    ax.set_xticks([i+shift*1.5 for i in range(len(technologies))])  # Position at the center of the groups
    
    if not bottom:
        ax.set_xticklabels(['','','',''])
    else:
        ax.set_xticklabels(['AP SMR', 'AP CCS', 'AP BH2S', 'AP AEC'], rotation=45, fontweight='bold')
       
    ax2 = ax.twinx()
    # Set labels and limits
    if left:
        ax2.set_ylabel(r'Carbon Intensity [$\frac{kgCO_2 \ eq}{Kg \ H_2}$]', rotation=270, fontweight='bold')
        ax2.yaxis.set_label_coords(1.25, 0.5)
        
    if isGrid:
        ax2.set_ylim(-1,25)
    else:
        ax2.set_ylim(-1,11)
    # ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    # ax.axhline(y=4, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.25)
    ax.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
    
    
    # Create custom legend
    legend_elements = [Patch(facecolor=colors[i], edgecolor='black', label=ci_subcategories[i]) for i in range(len(ci_subcategories))]
    if show_legend:
        ax.legend(handles=legend_elements, loc='upper right', facecolor='white', edgecolor='black')
        # ax.legend_.set_bbox_to_anchor((1,1))

    # Add a text annotation
    # ax.text(4.5,4.3, 'IRA 45V Threshold', ha='center', va='center', fontweight='bold', fontsize=9)
    
import matplotlib.ticker as ticker   
# def plot_sheet_subplot(sheet, colors, ax, alpha=0.2, show_legend=False, left=False, top=False):
#     """
#     This function plots the mean values of each technology over time with error bands into a subplot.
#
#     Parameters:
#     sheet (DataFrame): The dataframe to be plotted.
#     colors (dict): A dictionary of colors for each technology.
#     ax (matplotlib.axes.Axes): The axes object to plot into.
#     alpha (float): The alpha level for the error bands.
#
#     Returns:
#     None. The function plots a figure into the provided axes object.
#     """
#     ax2 = ax.twinx()
#     for tech in technologies2:
#         tech_data = sheet.loc[tech]
#         mean_values = tech_data.mean()
#         min_values = tech_data.min()
#         max_values = tech_data.max()
#
#         # Convert indices to integers for plotting
#         mean_values.index = mean_values.index.astype(int)
#         min_values.index = min_values.index.astype(int)
#         max_values.index = max_values.index.astype(int)
#
#         ax2.plot(mean_values.index, mean_values.values, color=colors[tech], label=tech)
#         ax2.fill_between(min_values.index, min_values.values, max_values.values, color=colors[tech], alpha=alpha)
#
#         if 'CBAM' in figure_ending_name:
#             ax2.plot(mean_values.index, 8.82*(1-0.014)**(mean_values.index-mean_values.index[0]), color='gray', linestyle=':', linewidth=1.5)
#             ax2.text(2027, 6.95, 'EU AP Reference', ha='left', va='baseline', rotation=-10, fontweight='bold')
#     ax.yaxis.set_ticks_position('none')
#     # ax.set_xlabel('Year', fontweight='bold')
#     ax.set_xlim(2023,2050)
#     ax.yaxis.set_visible(False)
#
#     ax2.axhline(y=4, color='black', linestyle='--', linewidth=1)
#     ax2.text(2023.1, 4.1, '45V Threshold', ha='left', va='baseline', rotation=0, fontweight='bold')
#
#
#
#
#     if top:
#         ax2.set_ylim(0,25)
#     else:
#         ax2.set_ylim(0,25)
#
#     if left:
#         ax2.set_ylabel(r'Carbon Intensity [$\frac{kgCO_2 \ eq}{Kg \ H_2}$]', rotation=270, fontweight='bold')
#         ax2.yaxis.set_label_coords(1.3, 0.5)
#     if show_legend:
#         ax2.legend()
#     ax.set_xticks(np.arange(2023, 2050, 6))
#
# plt.rcParams.update({'font.size': 14})
#
# sns.set(style='ticks')
# # Create a figure with 4 subplots
# fig, axs = plt.subplots(2, 4, figsize=(14, 11),gridspec_kw={'width_ratios': [1.1, 1.1, 1.1, 1.1], 'height_ratios': [1, 1], 'wspace': 0.22, 'hspace': 0.15})
#
# # Compare policy scenarios and plot the results for each pair of sheets
# compare_policy_scenarios_subplot(allData['1A'][columns], allData['1Aref'][columns], columns, reference=allData['1A']['AP_NPV'], ax=axs[0, 0], title='({}) Baseline US power grid'.format(year+3), show_legend=False, bottom=False,left= True)
# compare_policy_scenarios_subplot(allData['1B'][columns], allData['1Bref'][columns], columns, reference=allData['1B']['AP_NPV'], ax=axs[0, 1], title='({}) IRA compatible US power grid'.format(year+3), show_legend=True, bottom=False, left= False)
# compare_policy_scenarios_subplot(allData['1C'][columns], allData['1Cref'][columns], columns, reference=allData['1C']['AP_NPV'], ax=axs[1, 0], title='({}) Build and own'.format(year+3), show_legend=False, bottom=True, left= True)
# compare_policy_scenarios_subplot(allData['1D'][columns], allData['1Dref'][columns], columns, reference=allData['1D']['AP_NPV'], ax=axs[1, 1], title='({}) Power Purchase Agreement'.format(year+3), show_legend=False, bottom=True, left= False)
#
# technologies2 = ['AP SMR', 'AP CCS', 'AP BH2S', 'AP AEC']
# file_path = time_varying_filepath
# sheet_names = ['1A', '1B','1C','1D']
# sheets = clean_and_prepare_data(file_path, sheet_names, technologies2)
# # Define the colors
# colors = ["gray", "#4169E1", "#FF4500", "#008000"]
#
# # Create a dictionary that maps each technology to a color
# colors = dict(zip(technologies2, colors))
# # Plot stacked bar charts for each scenario
# # plot_stacked_bar_subplot(allData['1A'], technologies, axs[0, 2], False, isGrid=True, bottom=False,left= False)
# plot_sheet_subplot(sheets['1A'], colors, axs[0,2], top=True)
# axs[0, 2].set_title('Baseline US power grid', fontweight='bold')
# # plot_stacked_bar_subplot(allData['1B'], technologies, axs[0, 3], False, isGrid=True, bottom=False, left= True)
# plot_sheet_subplot(sheets['1B'], colors, axs[0,3], show_legend=True, left=True, top=True)
# axs[0, 3].set_title('IRA compatible US power grid', fontweight='bold')
#
# # plot_stacked_bar_subplot(allData['1C'], technologies, axs[1, 2], False, bottom=True, left= False)
# plot_sheet_subplot(sheets['1C'], colors, axs[1,2])
# axs[1, 2].set_title('Build and own', fontweight='bold')
# # plot_stacked_bar_subplot(allData['1D'], technologies, axs[1, 3], True, bottom=True, left= True)
# plot_sheet_subplot(sheets['1D'], colors, axs[1,3], left=True)
# axs[1, 3].set_title('Power Purchase Agreement', fontweight='bold')
#
# # Adjust the y-axis limits for each subplot to be 90% of the bottom whisker of the lowest box plot
# # and 110% of the top whisker of the highest box plot
# # for ax in axs.flatten():
# #     y_min, y_max = ax.get_ylim()
# #     ax.set_ylim(y_min*0.9, y_max*1.1)
# # for ax in axs[:, :].flatten():
#     # ax.tick_params(axis='x', which='both', length=0)
#     # ax.set_aspect(0.005)
# # Adjust the layout
#
# plt.tight_layout()
#
# plt.savefig('NPV/NPV{}_{}.png'.format(year, figure_ending_name), dpi=400)
# # Show the plot
# plt.close()
#
#
# # In[15]:
#

def scatter_plot_with_multiple_lines(scenario_names, dataframes, scenario_labels, fontsize):
    # Create a new figure with a 2x2 grid of subplots
    fig, axs = plt.subplots(2, 2, figsize=(14, 11), sharey=True)
    sns.set(style='ticks')
    # Variables to plot
    variables = [('AP_CCS_NPV', 'AP_CCS_CAC'), ('AP_BH2S_NPV', 'AP_BH2S_CAC'), ('AP_AEC_NPV', 'AP_AEC_CAC')]
    legend_labels = ['AP CCS', 'AP BH2S', 'AP AEC']
    
    # For each scenario
    for scenario_name, scenario_label, ax in zip(scenario_names, scenario_labels, axs.flatten()):
        # Get the DataFrame for the scenario
        df = dataframes[scenario_name]
        
        # For each pair of variables
        for i, ((y_var, x_var), legend_label) in enumerate(zip(variables, legend_labels)):
            # Get the X and Y data from the DataFrame
            x_data = df[x_var]
            y_data = df[y_var]
            
            # Create a scatter plot for each X and Y pair
            color = ['blue', 'orange', 'green'][i]
            marker = ['o','^','X'][i]
            ax.scatter(x_data, y_data, label=legend_label, color=color, s=30, alpha=0.2, edgecolor=color, linewidths=0, marker=marker)
        
        # Set labels and title
        ax.set_xlabel(r'Carbon Abatement Cost [$\mathbf{\frac{2023\$}{Tonne \ CO_2}}$]',fontsize=fontsize, fontweight='bold')
        ax.set_ylabel(r'NPV [$\mathbf{\frac{2023\$}{Tonne \ NH_3}}$]',fontsize=fontsize, fontweight='bold')
        # ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax.set_xlim(0,250)
        ax.set_ylim(NPV_low*0.8, 500)
        ax.set_title(scenario_label, fontweight='bold',fontsize=fontsize)
        
        # Create the legend
        if ax is axs[0, 1]:  # only create the legend for the last subplot
            legend = ax.legend(frameon=True, edgecolor='black',fontsize=fontsize, framealpha=0)
            legend.get_frame().set_linewidth(0)
            # Adjust the legend position
            # legend.set_bbox_to_anchor((1.05, 0.5))
            for i in range(len(legend.legendHandles)):
                legend.legendHandles[i]._sizes = [75]
                legend.legendHandles[i].set_alpha(1)
        if ax is axs[0,1] or ax is axs[1,1]:
            ax.set_ylabel("")
        
        if ax is axs[0,0] or ax is axs[0,1]:
            ax.set_xlabel("")
        
        # ax.axvline(x=70, linestyle='-', color='gray')
        # ax.axvline(x=4, linestyle='-', color='gray')
        # ax.axvline(x=28, linestyle='-', color='gray')
        # ax.axvline(x=32, linestyle='-', color='gray')
        # ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        # ax.text(69,500, 'Europe 2021', ha='center', va='center', rotation=90, fontweight='bold')
        # ax.text(27,500, 'Korea 2020', ha='center', va='center', rotation=90, fontweight='bold')
        # ax.text(31, 500, 'Canada 2021', ha='center', va='center', rotation=90, fontweight='bold')
        # ax.text(3, 500, 'China 2021', ha='center', va='center', rotation=90, fontweight='bold')
        ax.fill_betweenx(ax.get_ylim(), 18, 20, color='gray', alpha=0.2)
        ax.text(15, -50, 'California 2020-2022', ha='center', va='center', rotation=90, fontweight='bold')
        
        ax.fill_betweenx(ax.get_ylim(), 190, 230, color='gray', alpha=0.2)
        ax.text(200, -50, '2020-2030 SC of Carbon (2.0% Discount)', ha='center', va='center', rotation=90, fontweight='bold')
        
        ax.fill_betweenx(ax.get_ylim(), 110, 140, color='gray', alpha=0.2)
        ax.text(125, -50, '2020-2030 SC of Carbon (2.5% Discount)', ha='center', va='center', rotation=90, fontweight='bold')
        
        ax.fill_betweenx(ax.get_ylim(), 30, 89, color='gray', alpha=0.2)
        ax.text(60, -50, 'EU 2020-2022', ha='center', va='center', rotation=90, fontweight='bold')
        
        ax.grid(False)
    plt.tight_layout()
    plt.savefig("CAC/CACNPV main {}_{}.png".format(year,figure_ending_name), dpi=400)

    plt.close()

# # Call the function with the scenario names and labels
# scenario_names = ['1A', '1B', '1C', '1D']
# scenario_labels = ['({}) Baseline US power grid'.format(year+3), '({}) IRA compatible US power grid'.format(year+3), '({}) Build and own'.format(year+3), '({}) Power Purchase Agreement'.format(year+3)]
# scatter_plot_with_multiple_lines(scenario_names, allData, scenario_labels, 18)


# # Initialize the figure
# fig, axes = plt.subplots(2, 2, figsize=(14, 11))
#
# # Flatten the axes
# axes = axes.flatten()
#
# # Set the style of the plots
# sns.set_style("whitegrid")
# sns.set_palette("tab10")
#
# # Increase the font size
# sns.set_context("talk")
#
# # Define the sheets to plot
# sheets_to_plot = ["1A", "1B", "1C", "1D"]
# pairs_to_plot = [("AP_CCS_CE", "AP_CCS_Potential"), ("AP_BH2S_CE", "AP_BH2S_Potential"), ("AP_AEC_CE", "AP_AEC_Potential")]
# color_map = {"AP_CCS": "tab:blue", "AP_BH2S": "tab:orange", "AP_AEC": "tab:green"}
# scenario_labels = ['({}) Baseline US power grid'.format(year+3), '({}) IRA compatible US power grid'.format(year+3), '({}) Build and own'.format(year+3), '({}) Power Purchase Agreement'.format(year+3)]

# Loop over the sheets
# for i, sheet in enumerate(sheets_to_plot):
#     # Load the data
#     data = pd.read_excel(excel_file_path, sheet_name=sheet)
#
#     # Plot the cumulative probability distribution for each pair
#     for pair in pairs_to_plot:
#         for col in pair:
#             # Sort the data
#             sorted_vals = np.sort(data[col])
#             # Calculate the cumulative probabilities
#             cum_prob = np.arange(len(sorted_vals)) / float(len(sorted_vals) - 1)
#
#             # Determine the color and label
#             color_key = "_".join(col.split("_")[:2])  # Include 'AP_' prefix when creating the key
#             color = color_map[color_key]
#             if "Potential" in col:
#                 label = "Potential " + color_key.replace("_", " ")  # Label for _Potential plots
#             else:
#                 label = color_key.replace("_", " ")  # Label for _CE plots
#
#             # Determine the line style
#             line_style = '--' if "Potential" in col else '-'
#
#             # Plot the CDF
#             axes[i].plot(sorted_vals, cum_prob*4, label=label, color=color, linestyle=line_style, linewidth=2.5)
#
#     # Set the title
#     axes[i].set_title(scenario_labels[i], fontweight='bold', fontsize=20)
#     axes[i].set_ylim(0,1)
#     axes[i].set_xlim(0,5)
#
#     # Set the labels
#     axes[i].set_xlabel(r'Total Policy Support [$\frac{2023\$ \ PV_{Tax Credits}}{CAPEX}$]', fontsize=20)
#     axes[i].set_ylabel("Cumulative Probability", fontsize=20)
#     axes[i].grid(False)
#     axes[i].tick_params(axis='both', which='major', labelsize=18)
#     for _, spine in axes[i].spines.items():
#         spine.set_color('black')
#     # Remove legend for all but top right plot
#     if i != 1:
#         legend = axes[i].legend()
#         if legend:
#             legend.remove()
#
# # Add a legend to the top right plot
# axes[1].legend(loc='lower right')
#
# # Adjust the layout
# plt.tight_layout()
#
# plt.savefig("TC_Cumul/potential TCs {}_{}.png".format(year,figure_ending_name), dpi=400)
# # Show the plot
#
# # Set the style of the plots
# sns.set_style("whitegrid")
# sns.set_palette("tab10")
#
# # Increase the font size
# sns.set_context("talk")
#
# # Define the sheets to plot
# sheets_to_plot = ["1A", "1B", "1C", "1D"]
# pairs_to_plot = [("AP_CCS_CE", "AP_CCS_Potential"), ("AP_BH2S_CE", "AP_BH2S_Potential"), ("AP_AEC_CE", "AP_AEC_Potential")]
# color_map = {"AP_CCS": "tab:blue", "AP_BH2S": "tab:orange", "AP_AEC": "tab:green"}
# scenario_labels = ['({}) Baseline US power grid'.format(year+3), '({}) IRA compatible US power grid'.format(year+3), '({}) Build and own'.format(year+3), '({}) Power Purchase Agreement'.format(year+3)]
#
# # Function to create the desired box plot
# def create_box_plot():
#     # Initialize the figure
#     fig, axes = plt.subplots(2, 2, figsize=(14, 11))
#
#     # Flatten the axes
#     axes = axes.flatten()
#
#     # Custom color palette
#     custom_palette = {"Cash-Equivalent": "lightpink", "Potential": "gray"}
#
#     # Loop over the sheets and create box plots
#     for i, sheet in enumerate(sheets_to_plot):
#         # Load the data
#         data = pd.read_excel(excel_file_path, sheet_name=sheet)
#
#         # Create a DataFrame to store data for box plotting
#         box_plot_data = []
#
#         # Add data for each pair
#         for pair in pairs_to_plot:
#             for col in pair:
#                 # Determine the label and type
#                 label = "_".join(col.split("_")[:2])
#                 value_type = "Potential" if "Potential" in col else "Cash-Equivalent"
#                 box_plot_data.append(pd.DataFrame({'Value': data[col], 'Group': [label] * len(data), 'Type': [value_type] * len(data)}))
#
#         # Concatenate the DataFrames
#         box_plot_data = pd.concat(box_plot_data)
#
#
#         # Create the box plot
#         sns.boxplot(x='Group', y='Value', hue='Type', data=box_plot_data, ax=axes[i], palette=custom_palette, width=0.5)
#         axes[i].set_xlabel('')
#         # Set the title
#         axes[i].set_title(scenario_labels[i], fontweight='bold', fontsize=20)
#         axes[i].set_xticklabels([label.get_text().replace('_', ' ') for label in axes[i].get_xticklabels()])
#
#         # Set the labels
#         axes[i].set_ylabel(r'Total Policy Support [$\frac{2023\$ \ PV_{Tax Credits}}{CAPEX}$]', fontsize=20)
#         axes[i].tick_params(axis='both', which='major', labelsize=18)
#         axes[i].set_ylim(0,2.5)
#         for _, spine in axes[i].spines.items():
#             spine.set_color('black')
#
#         # Remove the legend if not the top right plot
#         if i != 1:
#             axes[i].legend().remove()
#
#     # Adjust the legend for the top right plot
#     axes[1].legend(framealpha=0, title=None, fontsize=16)
#
#     # Adjust the layout
#     plt.tight_layout()
#     plt.savefig('TC_Boxplot/Total_support_box_plot_{}_{}.png'.format(year, figure_ending_name), dpi=400)
#     # Show the plot

# # Call the function to create the plot
# create_box_plot()

# Define the function to plot the average electricity price
def plot_average_electricity_price(file_path, x_low, x_high):
    # Read the data from the Excel file
    data = pd.read_excel('TC_FINAL_alldata_v12_monthly.xlsx', sheet_name='El')
    sns.set_style('ticks')
    # Filter the data for time 2023
    new_data_2023 = data[data['time'] == 2023]

    # print(new_data_2023)
    # Function to convert the string of numbers (with brackets) to a list of floats
    def string_to_float_list(value):
        # Remove square brackets and split by space
        return [float(x) for x in value[1:-1].split() if x]

    # Apply the conversion to the "Grid Electricity" column
    new_data_2023['Grid Electricity'] = new_data_2023['Grid Electricity'].apply(string_to_float_list)

    # print(new_data_2023)
    # Function to calculate the average values for a given scenario and column
    def calculate_average_values(data, scenario, column_name):
        scenario_data = data[data['scenario'] == scenario]
        avg_values = [sum(x) / len(x) for x in zip(*scenario_data[column_name])]
        print(avg_values)
        return avg_values

    def fill_between_horizontal(x_values, y1, y2, color='gray', label=None, alpha=0.5):
        """
        Fills the area between two horizontal values y1 and y2 over the given x_values range.

        Parameters:
        - x_values: List of x-axis values.
        - y1: First y-value.
        - y2: Second y-value.
        - color: Color of the filled area. Default is 'gray'.
        - label: Label for the filled area. Default is None.
        - alpha: Opacity of the filled area. Default is 0.5.
        """
        plt.text(2025+45*y2, (y2-y1)/2+y2, label, fontsize=12, color='black')
        plt.fill_between(x_values, y1, y2, color=color, alpha=alpha)

    # Calculate the average "Grid Electricity" values for scenario A
    # average_grid_electricity_A = calculate_average_values(new_data_2023, 'A', 'Grid Electricity')

    # Calculate the average "Grid Electricity" values for scenario B
    average_grid_electricity_B = calculate_average_values(new_data_2023, 'B', 'Grid Electricity')
    # print(average_grid_electricity_B)
    # Horizontal lines and labels
    horizontal_lines = [
        (0.105, '2026 Scenario D PPA IRA'),
        (0.115, '2026 Scenario D PPA No Policy'),
        (0.0871, '2033 Scenario D PPA IRA'),
        (0.0966, '2033 Scenario D PPA No Policy')
    ]
    horizontal_line_colors = ['red', 'green', 'blue', 'purple']

    # Define x-axis values as years starting from January 2023
    x_values = [2023 + i / 12 for i in range(len(average_grid_electricity_B))]
    # print(average_grid_electricity_A)
    # Plot the mean values for scenarios A and B with distinct colors
    plt.figure(figsize=(12, 9))
    # plt.plot(x_values, average_grid_electricity_A, label='Scenario A AEO 2023', color='black')
    plt.plot(x_values, average_grid_electricity_B, label='Scenario A AEO 2023', color='gray')

    policies = [True, False]
    times = [2023,2030]
    bounds = ['low', 'high']
    matchings = ['hourly', 'monthly', 'yearly']

    # PPAs = {
    #     2023: {
    #         'hourly': {
    #             True: {
    #                 'low': PPA_data['LCOE'].iloc[16],
    #                 'high': PPA_data['LCOE'].iloc[17]
    #             },
    #             False: {
    #                 'low': PPA_data['LCOE'].iloc[18],
    #                 'high': PPA_data['LCOE'].iloc[19]
    #             }
    #         },
    #         'monthly': {
    #             True: {
    #                 'low': PPA_data['LCOE'].iloc[8],
    #                 'high': PPA_data['LCOE'].iloc[9]
    #             },
    #             False: {
    #                 'low': PPA_data['LCOE'].iloc[10],
    #                 'high': PPA_data['LCOE'].iloc[11]
    #             },
    #         },
    #         'yearly': {
    #             True: {
    #                 'low': PPA_data['LCOE'].iloc[0],
    #                 'high': PPA_data['LCOE'].iloc[1]
    #             },
    #             False: {
    #                 'low': PPA_data['LCOE'].iloc[2],
    #                 'high': PPA_data['LCOE'].iloc[3]
    #             },
    #         }
    #     },
    #     2030: {
    #         'hourly': {
    #             True: {
    #                 'low': PPA_data['LCOE'].iloc[20],
    #                 'high': PPA_data['LCOE'].iloc[21]
    #             },
    #             False: {
    #                 'low': PPA_data['LCOE'].iloc[22],
    #                 'high': PPA_data['LCOE'].iloc[23]
    #             }
    #         },
    #         'monthly': {
    #             True: {
    #                 'low': PPA_data['LCOE'].iloc[12],
    #                 'high': PPA_data['LCOE'].iloc[13]
    #             },
    #             False: {
    #                 'low': PPA_data['LCOE'].iloc[14],
    #                 'high': PPA_data['LCOE'].iloc[15]
    #             }
    #         },
    #         'yearly': {
    # }
    # }

    def recursive_multiply_dict_values(dictionary, multiplier):
        multiplied_dict = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                multiplied_dict[key] = recursive_multiply_dict_values(value, multiplier)
            else:
                multiplied_dict[key] = value * multiplier
        return multiplied_dict

    # PPAs = recursive_multiply_dict_values(PPAs, 1/1000)
    #
    #
    # color_sets = {
    #     2023: {
    #         'hourly': {
    #             True: '#FF0000',  # Bright Red
    #             False: '#B30000'  # Dim Red
    #         },
    #         'monthly': {
    #             True: '#0000FF',  # Bright Blue
    #             False: '#0000B3'  # Dim Blue
    #         },
    #         'yearly': {
    #             True: '#40E0D0',  # Bright Blue
    #             False: '#20B2AA'  # Dim Blue
    #         }
    #
    #     },
    #     2030: {
    #         'hourly': {
    #             True: '#00FF00',  # Bright Green
    #             False: '#00B300'  # Dim Green
    #         },
    #         'monthly': {
    #             True: '#FFFF00',  # Bright Yellow
    #             False: '#B3B300'  # Dim Yellow
    #         },
    #         'yearly': {
    #             True: '#FF69B4',  # Bright Blue
    #             False: '#FF1493'  # Dim Blue
    #         }
    #
    #     }
    # }
    #
    # for policy in policies:
    #     for time in times:
    #         for matching in matchings:
    #             pass
    #             # fill_between_horizontal(x_values,
    #             #                         PPAs[time][matching][policy]['low'],
    #             #                         PPAs[time][matching][policy]['high'],
    #             #                         color= color_sets[time][matching][policy],
    #             #                         label= f"{time} PPA {'IRA' if policy else 'NP'} {matching} matching range",
    #             #                         alpha=0.1)

    # Plot the horizontal lines with distinct colors
    # for i, (value, label) in enumerate(horizontal_lines):
    #     plt.axhline(y=value, color=horizontal_line_colors[i], linestyle='--', label=label)

    plt.ylabel('Average Electricity Price [$/kWh]', fontsize=20)
    plt.xlabel('Year', fontsize=20)
    plt.xlim(2023, 2023 + 516 / 12)
    plt.ylim(x_low,x_high)
    plt.title('Average Electricity Price Over Time', fontsize=20)
    plt.legend(loc="upper left", framealpha=1)
    plt.grid(True)
    # plt.show()
    plt.savefig(f"other/electricity_prices{x_low},{x_high}.png", dpi=400)
    plt.tick_params(axis='both',labelsize=20)


# Test the function with the provided file
plot_average_electricity_price(all_data_file_path, 0.06, 0.1)



def string_to_float_list(value):
    # If the value is a string and contains tuples, use literal_eval to extract the values
    if isinstance(value, str) and ('(' in value or '[' in value):
        value = value.replace("(", "[").replace(")", "]")
        tuples_list = ast.literal_eval(value)
        return [float(x[0]) if isinstance(x, (tuple, list)) else float(x) for x in tuples_list]
    return value

def plot_columns(file_path):
    # Read the data from the Excel file
    data = pd.read_excel(file_path, sheet_name='CAPEX_OPEX')
    
    # Define a list of columns to be plotted
    columns_to_plot = ["AP_SMR_OPEX", "AP_CCS_OPEX", "AP_BH2S_OPEX", "AP_AEC_OPEX"]

    # Convert the relevant columns to lists of floats
    for column in columns_to_plot:
        data[column] = data[column].apply(string_to_float_list)

    # Define scenarios and time periods
    scenarios = ["A", "B", "C", "D"]
    time_periods = [2023, 2030]
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'orange']

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    axes = axes.flatten()
    
    # Iterate through the columns and plot the data
    for i, column in enumerate(columns_to_plot):
        ax = axes[i]
        color_idx = 0
        for time_period in time_periods:
            for scenario in scenarios:
                # Filter data by scenario and time
                filtered_data = data[(data['scenario'] == scenario) & (data['time'] == time_period)]
            
                # Calculate the average values for each time step
                average_values = [-sum(x) / len(x) for x in zip(*filtered_data[column])]

                # Define x-axis values
                x_values = [i for i in range(len(average_values))]

                # Plot the mean values for each scenario and time
                label = f'{time_period} Scenario {scenario}'
                ax.plot(x_values, average_values, label=label if column == "AP_CCS_OPEX" else "", color=colors[color_idx])
                color_idx += 1

        ax.set_ylabel(column.replace("_", " ")+ "[$/Tonne NH3]")
        ax.grid(False)

    # Add legend to the second plot
    axes[1].legend(loc="lower left", framealpha=0.5)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('Other/OPEX_over_time_{}.png'.format(figure_ending_name), dpi=400)

# Test the function with the provided file
file_path = all_data_file_path  # Replace with the correct path
plot_columns(file_path)










