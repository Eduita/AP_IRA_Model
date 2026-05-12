"""IRA tax credit calculator (45V, 45Q, 45Y, 48C, 48E)."""

import pandas as pd

from ap_ira_lib.core.carbon_intensity import CarbonIntensity


class TaxCreditCalculator:
    def __init__(
        self,
        technology: str,
        start_month: int,
        scenario: str,
        engineering_inputs: dict,
        financial_inputs: dict,
        carbon_intensity: dict,
        ira_credits: dict,
        final_capex: dict,
        electrode_cost: float,
        battery_and_turbine_data_final: dict,
        biomass_requirement: float,
        natural_gas_requirements: dict,
        electricity_requirements: dict,
        aeo22_data: pd.DataFrame,
        aeo23_data: pd.DataFrame,
        capex_inputs: dict,
    ):
        self.technology = technology
        self.start_month = start_month
        self.time = 2023 if self.start_month == 0 else 2030
        self.scenario = scenario
        self.policy_inputs = ira_credits
        self.carbon_intensity = carbon_intensity
        self.electrode_cost = electrode_cost
        self.battery_and_turbine_data_final = battery_and_turbine_data_final
        self.engineering_inputs = engineering_inputs
        self.financial_inputs = financial_inputs
        self.final_capex = final_capex
        self.biomass_requirement = biomass_requirement
        self.natural_gas_requirements = natural_gas_requirements
        self.aeo22_data = aeo22_data
        self.aeo23_data = aeo23_data
        self.elec_inputs = electricity_requirements
        self.capex_inputs = capex_inputs

        self.ci_calculator = CarbonIntensity(
            self.technology,
            self.carbon_intensity,
            self.scenario,
            self.financial_inputs,
            self.engineering_inputs,
            self.biomass_requirement,
            self.natural_gas_requirements,
            self.elec_inputs,
            self.aeo22_data,
            self.aeo23_data,
        )
        self.ap_smr_ci_calculator = CarbonIntensity(
            "AP SMR",
            self.carbon_intensity,
            self.scenario,
            self.financial_inputs,
            self.engineering_inputs,
            self.biomass_requirement,
            self.natural_gas_requirements,
            self.elec_inputs,
            self.aeo22_data,
            self.aeo23_data,
        )
        self.hydrogen_production_yearly = (
            self.engineering_inputs["H2"] * 365 * self.financial_inputs["availability"]
        )
        self.hydrogen_production_monthly = self.hydrogen_production_yearly / 12
        self.electricity_demand_monthly = (
            self.ci_calculator.electricity_requirements[self.technology][1]
            * 1000
            * 24
            * 30
            * self.financial_inputs["availability"]
        )

        self.start_operation_month = self.start_month + 36
        self.end_operation_month = self.start_operation_month + 12 * 40
        self.ap_smr_emissions_start = self.ap_smr_ci_calculator.total_emissions(self.start_month)
        self.technology_emissions_start = self.ci_calculator.total_emissions(self.start_month)
        self.difference_48c = self.policy_inputs["48C expiry"] - self.start_operation_month
        self.max_45v_tier = max(self.policy_inputs["45V"].values(), key=lambda x: x[1])[1]

    def _is_operating(self, month: int) -> bool:
        return self.start_operation_month <= month < self.end_operation_month

    def _is_within_lifetime(self, month: int, credit_lifetime_years: int) -> bool:
        end_credit_month = self.start_operation_month + 12 * credit_lifetime_years
        return self.start_operation_month <= month < end_credit_month

    def _get_45v_tier(self, carbon_intensity: float) -> float:
        if carbon_intensity >= self.max_45v_tier:
            return 0.0
        for tier, (lower_bound, upper_bound) in self.policy_inputs["45V"].items():
            if lower_bound <= carbon_intensity < upper_bound:
                return tier
        raise ValueError(f"Carbon intensity {carbon_intensity} outside all 45V tiers.")

    def calculate_45v(self, month: int) -> float:
        if self.technology in ["AP AEC", "AP BH2S", "AP CCS"]:
            if self._is_operating(month) and self._is_within_lifetime(
                month, self.policy_inputs["45V lifetime"]
            ):
                ci = self.ci_calculator.total_emissions(month - self.start_month)
                tier = self._get_45v_tier(ci)
                return tier * self.hydrogen_production_monthly * 1000
        return 0.0

    def calculate_45q(self, month: int) -> float:
        if self.technology == "AP CCS":
            if self._is_operating(month) and self._is_within_lifetime(
                month, self.policy_inputs["45Q lifetime"]
            ):
                ci = self.ci_calculator.stack_emissions()
                ap_smr_ci = self.ap_smr_ci_calculator.stack_emissions()
                co2_abated = max(0.0, ap_smr_ci - ci) * self.hydrogen_production_monthly
                return self.policy_inputs["45Q"] * co2_abated
        return 0.0

    def calculate_45y(self, month: int) -> float:
        if self.scenario == "C" and self.technology != "AP SMR":
            if self._is_operating(month) and month < self.policy_inputs["45Y expiry"]:
                tau = month % 12
                electricity_generated = self.elec_inputs["total_gen"][self.technology][tau]
                return (electricity_generated * 1000) * (self.policy_inputs["45Y"] / 100)
        return 0.0

    def calculate_48c(self, month: int) -> float:
        if not self._is_operating(month) or month >= self.policy_inputs["48C expiry"]:
            return 0.0

        ap_smr_ci = self.ap_smr_emissions_start
        tech_ci = self.technology_emissions_start

        if (ap_smr_ci - 0.8 * ap_smr_ci > ap_smr_ci - tech_ci) and (ap_smr_ci - tech_ci < 0):
            return 0.0
        if ap_smr_ci - tech_ci < 0:
            return 0.0

        if self.scenario != "C":
            if self.technology == "AP SMR":
                return 0.0
            elif self.technology != "AP AEC":
                return (
                    self.final_capex[self.technology]["CAPEX"] - self.final_capex["AP SMR"]["CAPEX"]
                ) * self.policy_inputs["48C"]
            else:
                return self.electrode_cost * self.policy_inputs["48C"]
        else:
            if self.technology == "AP SMR":
                return 0.0
            elif self.technology != "AP AEC":
                return (
                    abs(
                        (
                            self.final_capex[self.technology]["CAPEX"]
                            - self.battery_and_turbine_data_final[self.technology]
                        )
                        - self.final_capex["AP SMR"]["CAPEX"]
                    )
                    * self.policy_inputs["48C"]
                )
            else:
                return self.electrode_cost * self.policy_inputs["48C"]

    def calculate_48e(self, month: int) -> float:
        if not self._is_operating(month) or month >= self.policy_inputs["48C expiry"]:
            return 0.0

        if self.scenario == "C" and self.technology != "AP SMR":
            wind_capacity = self.capex_inputs["wind_capacity"][self.technology] * 1000
            battery_capacity = self.capex_inputs["battery_capacity"][self.technology] * 1000
            solar_capacity = self.capex_inputs["solar_capacity"][self.technology] * 1000

            wind_capex = self.capex_inputs[f"Wind turbine CAPEX {self.time}"] * wind_capacity
            battery_capex = (
                self.capex_inputs[f"Battery Storage CAPEX {self.time}"] / 4 * battery_capacity
            )
            solar_capex = self.capex_inputs[f"Solar PV CAPEX {self.time}"] * solar_capacity

            return (wind_capex + battery_capex + solar_capex) * self.policy_inputs["48E"]
        return 0.0
