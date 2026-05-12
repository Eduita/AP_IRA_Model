"""Carbon intensity calculator for ammonia production technologies."""

import pandas as pd


class CarbonIntensity:
    def __init__(
        self,
        technology: str,
        carbon_intensity: dict,
        scenario: str,
        financial_inputs: dict,
        engineering_inputs: dict,
        biomass_requirement: float,
        natural_gas_requirements: dict,
        electricity_requirements: dict,
        aeo22_data: pd.DataFrame,
        aeo23_data: pd.DataFrame,
    ):
        self.technology = technology
        self.aeo22_data = aeo22_data.values
        self.aeo23_data = aeo23_data.values
        self.carbon_intensity = carbon_intensity
        self.electricity_requirements = electricity_requirements
        self.natural_gas_requirements = natural_gas_requirements
        self.biomass_requirement = biomass_requirement if technology == "AP BH2S" else 0
        self.engineering_inputs = engineering_inputs
        self.financial_inputs = financial_inputs
        self.scenario = scenario

        self.hydrogen_production_yearly = (
            self.engineering_inputs["H2"] * 365 * self.financial_inputs["availability"]
        )
        hydrogen_production_kg_yearly = self.hydrogen_production_yearly * 1000
        electricity_demand_kwh_yearly = (
            self.electricity_requirements[self.technology][0]
            * 1000
            * 24
            * 365
            * self.financial_inputs["availability"]
        )
        self.ratio_h2_kwh = hydrogen_production_kg_yearly / electricity_demand_kwh_yearly

        natural_gas_demand_mmbtu_yearly = self.natural_gas_requirements[self.technology]
        natural_gas_demand_kwh_yearly = natural_gas_demand_mmbtu_yearly * 293.071

        carbon_capture_rate_complement = (
            self.carbon_intensity["stack"][self.technology]
            / self.carbon_intensity["stack"]["AP SMR"]
            if self.technology == "AP CCS"
            else 1
        )
        self.natural_gas_carbon_emissions = (
            natural_gas_demand_kwh_yearly
            * self.carbon_intensity["natural gas"]
            * carbon_capture_rate_complement
        )
        self.natural_gas_intensity_kg_h2 = (
            self.natural_gas_carbon_emissions / hydrogen_production_kg_yearly
        )

        biomass_carbon_emissions = (
            self.biomass_requirement * self.carbon_intensity["biomass"] * 1000
        )
        self.biomass_intensity_kg_h2 = biomass_carbon_emissions / hydrogen_production_kg_yearly

    def _convert_electricity_intensity(self, electricity_carbon_intensity: float) -> float:
        return electricity_carbon_intensity / self.ratio_h2_kwh

    def electricity_emissions(self, t: int) -> float:
        if self.scenario == "A":
            data = self.aeo22_data
        elif self.scenario == "B":
            data = self.aeo23_data
        elif self.scenario in ["C", "D"]:
            return 0.0
        else:
            raise ValueError(
                f"Invalid scenario: {self.scenario}. Must be one of ['A', 'B', 'C', 'D']"
            )
        electricity_carbon_intensity = (
            data[t] * list(self.carbon_intensity["electricity"].values())
        ).sum()
        return self._convert_electricity_intensity(electricity_carbon_intensity)

    def natural_gas_emissions(self) -> float:
        return self.natural_gas_intensity_kg_h2

    def biomass_emissions(self) -> float:
        return self.biomass_intensity_kg_h2

    def stack_emissions(self) -> float:
        return self.carbon_intensity["stack"][self.technology]

    def total_emissions(self, t: int) -> float:
        return (
            self.electricity_emissions(t)
            + self.natural_gas_emissions()
            + self.biomass_emissions()
            + self.stack_emissions()
        )
