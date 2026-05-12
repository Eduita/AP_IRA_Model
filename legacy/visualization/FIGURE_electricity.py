import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sys.path.append(r"/model_runner_backend")

from BASELINE_PPA_models import LCOE_dataset

PPA_data = LCOE_dataset
all_data_file_path = "alldata_v10_hourly.xlsx"


def plot_average_electricity_price(file_path, x_low, x_high):
    # Read the data from the Excel file
    data = pd.read_excel(file_path, sheet_name="El")
    sns.set_style("ticks")
    # Filter the data for time 2023
    new_data_2023 = data[data["time"] == 2023]

    # Function to convert the string of numbers (with brackets) to a list of floats
    def string_to_float_list(value):
        # Remove square brackets and split by space
        return [float(x) for x in value[1:-1].split() if x]

    # Apply the conversion to the "Grid Electricity" column
    new_data_2023["Grid Electricity"] = new_data_2023["Grid Electricity"].apply(
        string_to_float_list
    )

    # Function to calculate the average values for a given scenario and column
    def calculate_average_values(data, scenario, column_name):
        scenario_data = data[data["scenario"] == scenario]
        avg_values = [sum(x) / len(x) for x in zip(*scenario_data[column_name])]
        return avg_values

    global n
    n = 0

    def fill_between_horizontal(x_values, y1, y2, color="gray", label=None, alpha=0.5, n=n):
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
        n += 1

        if n % 2 == 0:
            alternator = 300
        else:
            alternator = 0
        if matching == "monthly":
            label = ""
        plt.text(2025 + 90 * y2 + alternator, (y2 - y1) / 2 + y2, label, fontsize=12, color="black")
        plt.fill_between(x_values, y1, y2, color=color, alpha=alpha)

    # Calculate the average "Grid Electricity" values for scenario A
    average_grid_electricity_A = calculate_average_values(new_data_2023, "A", "Grid Electricity")

    # Calculate the average "Grid Electricity" values for scenario B
    average_grid_electricity_B = calculate_average_values(new_data_2023, "B", "Grid Electricity")

    # Horizontal lines and labels
    horizontal_lines = [
        (0.105, "2026 Scenario D PPA IRA"),
        (0.115, "2026 Scenario D PPA No Policy"),
        (0.0871, "2033 Scenario D PPA IRA"),
        (0.0966, "2033 Scenario D PPA No Policy"),
    ]
    horizontal_line_colors = ["red", "green", "blue", "purple"]

    # Define x-axis values as years starting from January 2023
    x_values = [2023 + i / 12 for i in range(len(average_grid_electricity_A))]

    # Plot the mean values for scenarios A and B with distinct colors
    plt.figure(figsize=(12, 9))
    plt.plot(x_values, average_grid_electricity_A, label="Scenario A AEO 2023", color="black")
    plt.plot(x_values, average_grid_electricity_B, label="Scenario B AEO 2022", color="gray")

    policies = [True, False]
    times = [2023, 2030]
    bounds = ["low", "high"]
    matchings = ["hourly", "monthly", "yearly"]

    PPAs = {
        2023: {
            "hourly": {
                True: {"low": PPA_data["LCOE"].iloc[16], "high": PPA_data["LCOE"].iloc[17]},
                False: {"low": PPA_data["LCOE"].iloc[18], "high": PPA_data["LCOE"].iloc[19]},
            },
            "monthly": {
                True: {"low": PPA_data["LCOE"].iloc[8], "high": PPA_data["LCOE"].iloc[9]},
                False: {"low": PPA_data["LCOE"].iloc[10], "high": PPA_data["LCOE"].iloc[11]},
            },
            "yearly": {
                True: {"low": PPA_data["LCOE"].iloc[0], "high": PPA_data["LCOE"].iloc[1]},
                False: {"low": PPA_data["LCOE"].iloc[2], "high": PPA_data["LCOE"].iloc[3]},
            },
        },
        2030: {
            "hourly": {
                True: {"low": PPA_data["LCOE"].iloc[20], "high": PPA_data["LCOE"].iloc[21]},
                False: {"low": PPA_data["LCOE"].iloc[22], "high": PPA_data["LCOE"].iloc[23]},
            },
            "monthly": {
                True: {"low": PPA_data["LCOE"].iloc[12], "high": PPA_data["LCOE"].iloc[13]},
                False: {"low": PPA_data["LCOE"].iloc[14], "high": PPA_data["LCOE"].iloc[15]},
            },
            "yearly": {
                True: {"low": PPA_data["LCOE"].iloc[4], "high": PPA_data["LCOE"].iloc[5]},
                False: {"low": PPA_data["LCOE"].iloc[6], "high": PPA_data["LCOE"].iloc[7]},
            },
        },
    }

    def recursive_multiply_dict_values(dictionary, multiplier):
        multiplied_dict = {}
        for key, value in dictionary.items():
            if isinstance(value, dict):
                multiplied_dict[key] = recursive_multiply_dict_values(value, multiplier)
            else:
                multiplied_dict[key] = value * multiplier
        return multiplied_dict

    PPAs = recursive_multiply_dict_values(PPAs, 1 / 1000)

    color_sets = {
        2023: {
            "hourly": {
                True: "#FF0000",  # Bright Red
                False: "#B30000",  # Dim Red
            },
            "monthly": {
                True: "#0000FF",  # Bright Blue
                False: "#0000B3",  # Dim Blue
            },
            "yearly": {
                True: "#40E0D0",  # Bright Blue
                False: "#20B2AA",  # Dim Blue
            },
        },
        2030: {
            "hourly": {
                True: "#00FF00",  # Bright Green
                False: "#00B300",  # Dim Green
            },
            "monthly": {
                True: "#FFFF00",  # Bright Yellow
                False: "#B3B300",  # Dim Yellow
            },
            "yearly": {
                True: "#FF69B4",  # Bright Blue
                False: "#FF1493",  # Dim Blue
            },
        },
    }

    for policy in policies:
        for time in times:
            for matching in matchings:
                fill_between_horizontal(
                    x_values,
                    PPAs[time][matching][policy]["low"],
                    PPAs[time][matching][policy]["high"],
                    color=color_sets[time][matching][policy],
                    label=f"{time} PPA {'IRA' if policy else 'NP'} {matching} matching range",
                    alpha=0.1,
                )

    # Plot the horizontal lines with distinct colors
    # for i, (value, label) in enumerate(horizontal_lines):
    #     plt.axhline(y=value, color=horizontal_line_colors[i], linestyle='--', label=label)

    plt.ylabel("Average Electricity Price [$/kWh]")
    plt.xlabel("Year")
    plt.xlim(2023, 2023 + 516 / 12)
    plt.ylim(x_low, x_high)
    plt.title("Average Electricity Price Over Time")
    plt.legend(loc="upper left", framealpha=1)
    plt.grid(True)
    # plt.show()
    plt.savefig(f"Final figures/V10_electricity_prices{x_low},{x_high}.png", dpi=400)


# Test the function with the provided file
plot_average_electricity_price(all_data_file_path, 0, 0.5)
