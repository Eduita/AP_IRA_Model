import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

matching = "monthly"
CBAM = True

file_path_NPV = f"alldata_v10{'_CBAM' if CBAM else ''}_{matching}.xlsx"
file_path_sensitivity = f"sensitivities{'_' + matching}.xlsx"

NPV = pd.read_excel(file_path_NPV, sheet_name="NPV")
sensitivities = pd.read_excel(file_path_sensitivity, sheet_name=None)

NPV = NPV.rename(
    columns={
        "AP_SMR_NPV": "AP SMR",
        "AP_CCS_NPV": "AP CCS",
        "AP_BH2S_NPV": "AP BH2S",
        "AP_AEC_NPV": "AP AEC",
    }
)

technologies = ["AP SMR", "AP CCS", "AP BH2S", "AP AEC"]
scenarios = ["A", "B", "C", "D"]
times = [2023, 2030]

grouped_NPV = NPV.groupby(["time", "scenario"])

grouped_sensitivities = {
    key: sensitivities[key].groupby(["time", "scenario"]) for key in sensitivities
}

tech_dict_corr = {}
for tech in technologies:
    storage_of_corr_scenario_time = {
        time: {scenario: None for scenario in scenarios} for time in times
    }
    for (time, scenario), NPV_df in grouped_NPV:
        tech_NPV = NPV_df[tech]
        sensitivity_inputs_df = grouped_sensitivities[tech].get_group((time, scenario))
        input_columns = sensitivity_inputs_df.columns[3:]

        storage_of_corr = {}
        for col in input_columns:
            correlation = np.corrcoef(tech_NPV, sensitivity_inputs_df[col])[0, 1]
            storage_of_corr[col] = correlation

        storage_of_corr_scenario_time[time][scenario] = storage_of_corr

    tech_dict_corr[tech] = storage_of_corr_scenario_time


def replace_nan_with_zero_nested_dict(d):
    for key, value in d.items():
        if isinstance(value, dict):
            replace_nan_with_zero_nested_dict(value)
        elif isinstance(value, float) and math.isnan(value):
            d[key] = 0


replace_nan_with_zero_nested_dict(tech_dict_corr)


def plot_heatmap_for_scenario(time, scenario, data, ax=None, title=None, threshold=10.0):
    """
    Plot heatmap for a given scenario with ordered y-axis based on sum of absolute correlation coefficients.

    Parameters:
    - time: The specific time for which to plot the heatmap.
    - scenario: The scenario for which to plot the heatmap.
    - data: The correlation data dictionary.
    - ax: Optional axis object to plot the heatmap on.
    - title: Optional title for the heatmap.

    Returns:
    - ax: Axis object with the plotted heatmap.
    """

    # Extract data for the given time and scenario
    heatmap_data = pd.DataFrame(index=data[list(data.keys())[0]][time][scenario].keys())
    for tech in data.keys():
        heatmap_data[tech] = data[tech][time][scenario].values()

    # Filter the heatmap data based on the given threshold
    filtered_heatmap_data = heatmap_data[heatmap_data.abs().max(axis=1) > threshold / 100.0]

    # Convert the filtered heatmap data to percentages
    percentage_heatmap_data = filtered_heatmap_data * 100

    # Order the y-axis based on sum of absolute correlation coefficients
    ordered_data = percentage_heatmap_data.reindex(
        percentage_heatmap_data.abs().sum(axis=1).sort_values(ascending=False).index
    )

    # Plot the heatmap with given adjustments
    ax = sns.heatmap(
        ordered_data,
        cmap="Spectral",
        annot=True,
        fmt=".0f",
        vmin=-100,
        vmax=100,
        linewidths=0.5,
        ax=ax,
        cbar=False,
        edgecolor="pink",
    )
    ax.set_title(title if title else scenario, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")

    ax.set_xticklabels(
        [label.replace("_", " ").replace("AP ", "") for label in ordered_data.columns], rotation=0
    )

    return ax


fig, axs = plt.subplots(2, 3, figsize=(12, 12), gridspec_kw={"width_ratios": [4, 4, 4]})
fig.subplots_adjust(hspace=0.1, wspace=1.1, left=0.2)

ax_b = plot_heatmap_for_scenario(
    2023, "B", tech_dict_corr, ax=axs[0, 0], title=f"Scenario A, 2026", threshold=0
)
ax_b.set_xticks([])
ax_c = plot_heatmap_for_scenario(
    2023, "C", tech_dict_corr, ax=axs[0, 1], title=f"Scenario B, 2026", threshold=0
)
ax_c.set_xticks([])
ax_d = plot_heatmap_for_scenario(
    2023, "D", tech_dict_corr, ax=axs[0, 2], title=f"Scenario C, 2026", threshold=0
)
ax_d.set_xticks([])

ax_b_2030 = plot_heatmap_for_scenario(
    2030, "B", tech_dict_corr, ax=axs[1, 0], title=f"Scenario A, 2033", threshold=0
)
ax_c_2030 = plot_heatmap_for_scenario(
    2030, "C", tech_dict_corr, ax=axs[1, 1], title=f"Scenario B, 2033", threshold=0
)
ax_d_2030 = plot_heatmap_for_scenario(
    2030, "D", tech_dict_corr, ax=axs[1, 2], title=f"Scenario C, 2033", threshold=0
)


# Add a single colorbar to the figure
cbar_ax = fig.add_axes([0.92, 0.3, 0.02, 0.4])
cmap = sns.color_palette("Spectral", as_cmap=True)
norm = plt.Normalize(vmin=-100, vmax=100)
cb1 = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cbar_ax, format="%d%%")
cb1.set_label("Pearson Correlation Coefficient", rotation=270, fontweight="bold", labelpad=2)

plt.savefig(f"Final figures/v10_sensitivites_{'_CBAM' if CBAM else ''}_{matching}.png", dpi=400)
plt.close()
