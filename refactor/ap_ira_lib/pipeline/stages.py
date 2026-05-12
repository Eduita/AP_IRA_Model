"""Concrete pipeline stages for the AP IRA model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ap_ira_lib.core.capex import CAPEX
from ap_ira_lib.core.carbon_intensity import CarbonIntensity
from ap_ira_lib.core.dcf import StochasticDCF
from ap_ira_lib.core.opex import MIOPEX
from ap_ira_lib.inputs.parameters import ParameterSampler
from ap_ira_lib.io.data_cleaning import load_optimization_data, return_masked_random_row
from ap_ira_lib.io.excel import (
    back_calculate_depreciable_capital_factor,
    calculate_battery_and_turbine_cost,
    calculate_electrode_cost,
    calculate_final_CAPEX,
)
from ap_ira_lib.pipeline.base import SimContext, Stage

_EXCLUDE_FROM_DEPRECIATION = [
    "Engineering and Supervision Cost",
    "Legal Expenses Cost",
    "Construction Expense and Contractors Fee Cost",
    "Working Capital",
    "Contingency Cost",
    "Land Cost",
]


# ------------------------------------------------------------------ #
# Stage 1 — Parameter sampling
# ------------------------------------------------------------------ #

class ParameterSamplingStage(Stage):
    """Load JSON parameters and draw stochastic samples for this simulation."""

    stage_id = "parameter_sampling"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.parameters_file = Path(self.config["parameters_file"])

    def run(self, ctx: SimContext) -> dict[str, Any]:
        sampler = ParameterSampler(ctx.sim_index)
        params = sampler.sample(self.parameters_file)

        # Convert 45V keys to float (JSON keys are strings)
        params["IRA_credits"]["45V"] = {
            float(k): v for k, v in params["IRA_credits"]["45V"].items()
        }
        return {"params": params, "sampler": sampler}


# ------------------------------------------------------------------ #
# Stage 2 — Location & renewable capacity setup
# ------------------------------------------------------------------ #

class LocationSetupStage(Stage):
    """Assign wind/battery/solar capacity from optimization results for each technology."""

    stage_id = "location_setup"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.optimization_file = Path(self.config["optimization_file"])
        self._data: pd.DataFrame | None = None

    def _get_data(self) -> pd.DataFrame:
        if self._data is None:
            self._data = load_optimization_data(self.optimization_file)
        return self._data

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        data = self._get_data()

        rand_aec = float(np.random.uniform(0, 1))
        rand_loc = float(np.random.uniform(0, 1))

        def get_row(tech: str) -> pd.Series:
            return return_masked_random_row(data, ctx.time, ctx.matching, tech, rand_loc)

        def aec_interp(low_val, high_val):
            if isinstance(low_val, float) and isinstance(high_val, float):
                return low_val + (high_val - low_val) * rand_aec
            return [low_val[i] + (high_val[i] - low_val[i]) * rand_aec for i in range(len(low_val))]

        capex_inputs = params["CAPEX_inputs"]
        capex_inputs["wind_capacity"] = {}
        capex_inputs["battery_capacity"] = {}
        capex_inputs["solar_capacity"] = {}

        curtailment, discharge, total_gen = {}, {}, {}

        for tech in ctx.technologies[1:]:  # skip AP SMR
            if tech != "AP AEC":
                row = get_row(tech)
                capex_inputs["wind_capacity"][tech] = row["wind_capacity"]
                capex_inputs["battery_capacity"][tech] = row["battery_capacity"]
                capex_inputs["solar_capacity"][tech] = row["solar capacity"]
                curtailment[tech] = row["curtailment"]
                discharge[tech] = row["demand"]
                total_gen[tech] = row["total_gen"]
            else:
                row_high = get_row("AP AEC high")
                row_low = get_row("AP AEC low")
                capex_inputs["wind_capacity"][tech] = aec_interp(row_low["wind_capacity"], row_high["wind_capacity"])
                capex_inputs["battery_capacity"][tech] = aec_interp(row_low["battery_capacity"], row_high["battery_capacity"])
                capex_inputs["solar_capacity"][tech] = aec_interp(row_low["solar capacity"], row_high["solar capacity"])
                curtailment[tech] = aec_interp(row_low["curtailment"], row_high["curtailment"])
                discharge[tech] = aec_interp(row_low["demand"], row_high["demand"])
                total_gen[tech] = aec_interp(row_low["total_gen"], row_high["total_gen"])

        electricity_requirements = params["electricity_requirements"]
        electricity_requirements["curtailment"] = curtailment
        electricity_requirements["discharge"] = discharge
        electricity_requirements["total_gen"] = total_gen

        return {"rand_loc": rand_loc, "rand_aec": rand_aec}


# ------------------------------------------------------------------ #
# Stage 3 — Engineering derived quantities
# ------------------------------------------------------------------ #

class EngineeringSetupStage(Stage):
    """Derive AEC hydrogen requirement, operating hours, biomass, and depreciable factor."""

    stage_id = "engineering_setup"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        eng = params["engineering_inputs"]
        fin = params["financial_inputs"]
        capex_inputs = params["CAPEX_inputs"]
        elec = params["electricity_requirements"]

        fin["operating_hours_per_year"] = 365 * 24 * fin["availability"]
        eng["AP AEC H2_req"] = eng["H2"] * eng["H2 LHV"] / eng["Eff_electrolysis"] / 24

        elec["AP AEC"] = (
            eng["AP AEC H2_req"],
            eng["AP AEC H2_req"] + (408305790 + 3900560.592) / (365 * 24 * fin["availability"]) / 1000,
        )

        back_calculate_depreciable_capital_factor(capex_inputs, _EXCLUDE_FROM_DEPRECIATION)

        biomass_requirement = (eng["H2"] * 1000 / 70.4) * (365 * fin["availability"])
        biomass_price = float(np.random.uniform(50.68, 118.25))

        return {"biomass_requirement": biomass_requirement, "biomass_price": biomass_price}


# ------------------------------------------------------------------ #
# Stage 4 — Carbon intensity & market setup
# ------------------------------------------------------------------ #

class CarbonIntensitySetupStage(Stage):
    """Compute stack emissions, natural gas CI, and PPA pricing."""

    stage_id = "carbon_intensity_setup"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.ppa_file = Path(self.config["ppa_file"])
        self._ppa_data: pd.DataFrame | None = None
        self.times: list[int] = self.config.get("times", [2023, 2030])
        self.matching_types: list[str] = self.config.get("matching_types", ["yearly", "monthly", "hourly"])
        self.policies: list[bool] = [True, False]

    def _get_ppa_data(self) -> pd.DataFrame:
        if self._ppa_data is None:
            self._ppa_data = pd.read_excel(self.ppa_file)
        return self._ppa_data

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        rand_loc = ctx.data["rand_loc"]
        ci = params["carbon_intensity"]

        # Stack CI — sampled uniformly from physics bounds (Eq. SI)
        ngcc_eff = ci["NGCC thermal efficiency"]
        ap_smr_lower = 0.243 * ngcc_eff * 13.4 / 0.28
        ap_smr_upper = 0.527 * ngcc_eff * 13.4 / 0.28
        ci["stack"]["AP SMR"] = float(np.random.uniform(ap_smr_lower, ap_smr_upper))
        ci["stack"]["AP CCS"] = ci["stack"]["AP SMR"] * (1 - params["engineering_inputs"]["CCS capture rate"])

        # Natural gas CI
        ci["natural gas"] = (float(np.random.uniform(0.01, 7.9)) / 1000) * ngcc_eff

        # PPA pricing
        ppa_data = self._get_ppa_data()

        def get_ppa_row(time: int, matching: str, policy: bool) -> pd.Series:
            mask = (ppa_data["time"] == time) & (ppa_data["policy"] == policy) & (ppa_data["matching"] == matching)
            subset = ppa_data[mask]
            return subset.iloc[int(rand_loc * len(subset))]

        market_inputs = params["Market_inputs"]
        market_inputs["PPA_pricing"] = {
            t: {m: {p: get_ppa_row(t, m, p)["LCOE"] / 1000 for p in self.policies}
                for m in self.matching_types}
            for t in self.times
        }
        market_inputs["PPA_pricing_for_C"] = {
            t: {p: market_inputs["PPA_pricing"][t]["yearly"][p] for p in self.policies}
            for t in self.times
        }

        return {}


# ------------------------------------------------------------------ #
# Stage 5 — CAPEX calculation
# ------------------------------------------------------------------ #

class CAPEXStage(Stage):
    """Calculate CAPEX for each technology."""

    stage_id = "capex"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        capex_inputs = params["CAPEX_inputs"]
        basic_eq = params["basic_equipment_costs"]
        elec = params["electricity_requirements"]
        biomass_requirement = ctx.data["biomass_requirement"]

        final_capex: dict = {}
        battery_turbine: dict = {}
        electrode_costs: dict = {}

        for tech in ctx.technologies:
            bt = calculate_battery_and_turbine_cost(tech, ctx.time, capex_inputs)
            battery_turbine[tech] = bt

            elec_cost = (
                calculate_electrode_cost(ctx.time, elec, capex_inputs)
                if tech == "AP AEC"
                else 0.0
            )
            electrode_costs[tech] = elec_cost

            final_capex[tech] = calculate_final_CAPEX(
                tech, ctx.scenario, bt, elec_cost, basic_eq, capex_inputs
            )

        return {
            "final_capex": final_capex,
            "battery_turbine": battery_turbine,
            "electrode_costs": electrode_costs,
        }


# ------------------------------------------------------------------ #
# Stage 6 — OPEX calculation
# ------------------------------------------------------------------ #

class OPEXStage(Stage):
    """Calculate MI_OPEX for each technology."""

    stage_id = "opex"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        final_capex = ctx.data["final_capex"]
        biomass_requirement = ctx.data["biomass_requirement"]
        biomass_price = ctx.data["biomass_price"]
        mi_inputs = params["MI_OPEX_inputs"]
        fin = params["financial_inputs"]
        capex_inputs = params["CAPEX_inputs"]

        final_mi_opex: dict = {}

        for tech in ctx.technologies:
            calc = MIOPEX(
                processing_steps=mi_inputs["processing_steps"][tech],
                hourly_pay_per_operator=mi_inputs["operator_pay"],
                heuristics_factors=mi_inputs["heuristics_factors"],
                technology=tech,
                financial_inputs=fin,
                mi_opex_inputs=mi_inputs,
                final_capex=final_capex,
                hp_steam_requirements=params["HP_steam_requirements"],
                bfw_requirements=params["BFW_requirements"],
                biomass_price=biomass_price,
                biomass_requirement=biomass_requirement,
                capex_inputs=capex_inputs,
            )
            labor = calc.calculate_labor_costs()
            fixed = calc.fixed_charges()
            misc = calc.misc_up_costs()
            start = calc.get_start_up_costs()
            utilities = calc.utilities_costs()

            if ctx.scenario == "C" and tech != "AP SMR":
                wind_kw = capex_inputs["wind_capacity"][tech] * 1000
                battery_kw = capex_inputs["battery_capacity"][tech] * 1000
                battery_opex = mi_inputs["Battery OPEX"] * battery_kw / capex_inputs["Battery roundtrip eff"] / 12 / 4
                wind_opex = mi_inputs["Wind OPEX"] * wind_kw / 12
                final_mi_opex[tech] = {
                    "MI_OPEX": labor + fixed + misc + utilities + wind_opex + battery_opex,
                    "MI_OPEX_start": start,
                }
            else:
                final_mi_opex[tech] = {
                    "MI_OPEX": labor + fixed + misc + utilities,
                    "MI_OPEX_start": start,
                }

        return {"final_mi_opex": final_mi_opex}


# ------------------------------------------------------------------ #
# Stage 7 — DCF simulation
# ------------------------------------------------------------------ #

class DCFStage(Stage):
    """Run StochasticDCF for each technology and collect output metrics."""

    stage_id = "dcf"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.outputs_enabled: dict[str, bool] = self.config.get(
            "outputs_enabled",
            {"npv": True, "cac": True, "carbon_intensity": True, "tax_credits": True},
        )
        self.ci_years: list[int] = [2023 + i for i in range(28)]
        self.ci_months: list[int] = [12 * i for i in range(28)]

    def _make_dcf(self, technology: str, ctx: SimContext, params: dict) -> StochasticDCF:
        return StochasticDCF(
            technology=technology,
            start=ctx.start_month,
            L=ctx.L,
            sim=ctx.sim_index,
            policy=ctx.policy,
            scenario=ctx.scenario,
            financial_inputs=params["financial_inputs"],
            final_capex=ctx.data["final_capex"],
            capex_inputs=params["CAPEX_inputs"],
            engineering_inputs=params["engineering_inputs"],
            market_inputs=params["Market_inputs"],
            ira_credits=params["IRA_credits"],
            carbon_intensity=params["carbon_intensity"],
            natural_gas_requirements=params["natural_gas_requirements"],
            final_mi_opex=ctx.data["final_mi_opex"],
            electricity_requirements=params["electricity_requirements"],
            mi_opex_inputs=params["MI_OPEX_inputs"],
            electrode_cost=ctx.data["electrode_costs"][technology],
            biomass_requirement=ctx.data["biomass_requirement"],
            aeo22_data=ctx.data["aeo22_data"],
            aeo23_data=ctx.data["aeo23_data"],
            battery_and_turbine_data_final=ctx.data["battery_turbine"],
            is_cbam=ctx.is_cbam,
            matching=ctx.matching,
        )

    def run(self, ctx: SimContext) -> dict[str, Any]:
        params = ctx.data["params"]
        results: dict[str, Any] = {
            "npv": {}, "npv_no_policy": {}, "cac": {},
            "carbon_intensity": {tech: [] for tech in ctx.technologies},
            "tax_credits": {},
        }

        for tech in ctx.technologies:
            dcf = self._make_dcf(tech, ctx, params)
            dcf_np = self._make_dcf(tech, ctx, params)  # no-policy variant
            dcf_np.policy = False

            if self.outputs_enabled.get("npv", True):
                results["npv"][tech] = dcf.calculate_NPV()
                results["npv_no_policy"][tech] = dcf_np.calculate_NPV()

            if self.outputs_enabled.get("cac", True) and tech != "AP SMR":
                results["cac"][tech] = dcf.CAC_updated()

            if self.outputs_enabled.get("carbon_intensity", True):
                ci_calc = CarbonIntensity(
                    technology=tech,
                    carbon_intensity=params["carbon_intensity"],
                    scenario=ctx.scenario,
                    financial_inputs=params["financial_inputs"],
                    engineering_inputs=params["engineering_inputs"],
                    biomass_requirement=ctx.data["biomass_requirement"],
                    natural_gas_requirements=params["natural_gas_requirements"],
                    electricity_requirements=params["electricity_requirements"],
                    aeo22_data=ctx.data["aeo22_data"],
                    aeo23_data=ctx.data["aeo23_data"],
                )
                results["carbon_intensity"][tech] = [ci_calc.total_emissions(m) for m in self.ci_months]

            if self.outputs_enabled.get("tax_credits", True) and tech != "AP SMR":
                results["tax_credits"][tech] = dcf.separate_total_support()

        return {"dcf_results": results}
