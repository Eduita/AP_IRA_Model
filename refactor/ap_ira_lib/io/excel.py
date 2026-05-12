"""Excel I/O utilities and CAPEX helper functions."""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

from ap_ira_lib.core.capex import CAPEX


def dataframes_to_excel(dfs: dict, file_path: Path | str) -> None:
    """Write a dict of DataFrames to an Excel workbook (one sheet per key).

    Nested dicts produce sheets named ``<outer_key>_<inner_key>``.
    """
    try:
        with pd.ExcelWriter(file_path) as writer:
            for sheet_name, df in dfs.items():
                if isinstance(df, dict):
                    for sub_name, sub_df in df.items():
                        sub_df.to_excel(writer, sheet_name=f"{sheet_name}_{sub_name}", index=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Written to {file_path}")
    except Exception as exc:
        print(f"Error writing {file_path}: {exc}")


def get_current_est_time() -> str:
    tz = pytz.timezone("US/Eastern")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


def extract_wind_battery_values(time: int, matching: str, results_df: pd.DataFrame) -> dict:
    """Extract wind/battery/solar capacity from optimization results for a given time+matching."""
    extracted = {}
    for label, cap_desc, loc in [("high", "high", "high"), ("low", "low", "low")]:
        mask = (
            (results_df["time"] == time)
            & (results_df["matching"] == matching)
            & (results_df["capex_description"] == cap_desc)
            & (results_df["location"] == loc)
        )
        for _, row in results_df[mask].iterrows():
            tech = row["technology"]
            extracted[tech] = {
                "wind_capacity": row["wind_capacity"],
                "battery_capacity": row["battery_capacity"],
                "curtailment": ast.literal_eval(row["curtailment"]),
                "discharge": ast.literal_eval(row["discharge"]),
            }
    return extracted


def calculate_battery_and_turbine_cost(technology: str, time: int, capex_inputs: dict) -> float:
    if technology == "AP SMR":
        return 0.0
    wind_kw = capex_inputs["wind_capacity"][technology] * 1000
    battery_kw = capex_inputs["battery_capacity"][technology] * 1000
    solar_kw = capex_inputs.get("solar_capacity", {}).get(technology, 0) * 1000
    wind_capex = capex_inputs[f"Wind turbine CAPEX {time}"] * wind_kw
    battery_capex = capex_inputs[f"Battery Storage CAPEX {time}"] / 4 * battery_kw
    solar_capex = capex_inputs[f"Solar PV CAPEX {time}"] * solar_kw
    return wind_capex + battery_capex + solar_capex


def calculate_electrode_cost(
    time: int, electricity_requirements: dict, capex_inputs: dict
) -> float:
    key = "Stack cost 2023" if time == 2023 else "Stack cost 2030"
    return electricity_requirements["AP AEC"][1] * capex_inputs[key] * 1000


def calculate_final_capex(
    technology: str,
    scenario: str,
    battery_and_turbine: float,
    electrode_cost: float,
    basic_equipment_costs: dict,
    capex_inputs: dict,
) -> dict:
    obj = CAPEX(capex_inputs)
    obj.get_installed_and_uninstalled_cost(basic_equipment_costs, technology)
    obj.calculate_fci_capex_and_wc()

    if scenario == "C" and technology != "AP SMR":
        additional = battery_and_turbine + (electrode_cost if technology == "AP AEC" else 0.0)
        obj.add_cost_outside_of_equipment_list(additional)
    elif technology == "AP AEC":
        obj.add_cost_outside_of_equipment_list(electrode_cost)

    return obj.as_dict()


def back_calculate_depreciable_capital_factor(
    capex_inputs: dict, excluded_factors: list[str]
) -> None:
    """Compute CAPEX_from_installed_cost and store it in-place on capex_inputs."""
    keys = list(capex_inputs.keys())[1:12]
    factor = 1.0
    for key in keys:
        if key not in excluded_factors:
            factor += capex_inputs[key] * (1 / ((2717 / 100) ** 0.6))
    capex_inputs["CAPEX_from_installed_cost"] = factor
