"""Stochastic Discounted Cash Flow model for ammonia production technologies."""

import pandas as pd
from ap_ira_lib.core.gbm import BrownianMotion
from ap_ira_lib.core.carbon_intensity import CarbonIntensity
from ap_ira_lib.core.tax_credits import TaxCreditCalculator
from ap_ira_lib.io.excel import dataframes_to_excel


class StochasticDCF:
    def __init__(
        self,
        technology: str,
        start: int,
        L: int,
        sim: int,
        policy: bool,
        scenario: str,
        financial_inputs: dict,
        final_capex: dict,
        capex_inputs: dict,
        engineering_inputs: dict,
        market_inputs: dict,
        ira_credits: dict,
        carbon_intensity: dict,
        natural_gas_requirements: dict,
        final_mi_opex: dict,
        electricity_requirements: dict,
        mi_opex_inputs: dict,
        electrode_cost: float,
        biomass_requirement: float,
        aeo22_data: pd.DataFrame,
        aeo23_data: pd.DataFrame,
        battery_and_turbine_data_final: dict,
        is_cbam: bool = False,
        matching: str = "hourly",
        deterministic: bool = False,
    ):
        self.technology = technology
        self.policy = policy
        self.start = start
        self.scenario = scenario
        self.matching = matching
        self.is45V = None
        self.is48E = None

        self.financial_inputs = financial_inputs
        self.final_capex = final_capex
        self.capex_inputs = capex_inputs
        self.engineering_inputs = engineering_inputs
        self.market_inputs = market_inputs
        self.ira_credits = ira_credits
        self.carbon_intensity = carbon_intensity
        self.final_mi_opex = final_mi_opex
        self.elec_inputs = electricity_requirements
        self.mi_opex_inputs = mi_opex_inputs
        self.electrode_cost = electrode_cost
        self.natural_gas_requirements = natural_gas_requirements
        self.biomass_requirement = biomass_requirement
        self.aeo22_data = aeo22_data
        self.aeo23_data = aeo23_data
        self.battery_and_turbine_data_final = battery_and_turbine_data_final

        self.construction = self.financial_inputs["construction_time"]
        self.L = L
        self.inflation_rate = self.financial_inputs["inflation"]
        self.Y = self.financial_inputs["Y"]
        self.FCI = self.final_capex[self.technology]["FCI"]
        self.land_cost = self.capex_inputs["Land Cost"]
        self.WC = self.final_capex[self.technology]["WC"]
        self.r = self.financial_inputs["cost_of_debt"]
        self.e = self.financial_inputs["equity"]
        self.M_NH3 = self.engineering_inputs["NH3"]
        self.F_A = self.financial_inputs["availability"]
        self.H_operating = self.financial_inputs["operating_hours_per_year"]
        self.phi_state = self.financial_inputs["state_tax"]
        self.phi_federal = self.financial_inputs["federal_tax"]
        self.L_loan = self.financial_inputs["loan_lifetime"]
        self.L_equipment = self.financial_inputs["equipment_lifetime_depreciation"]
        self.C_equipment = self.final_capex[self.technology]["UC"]
        self.discount_rate = (
            self.e * self.financial_inputs["return_on_equity"]
            + (1 - self.e) * self.r * (1 - (self.phi_federal + self.phi_state))
        )
        self.sim = sim
        self.time = 2023 if self.start == 0 else 2030

        if self.start == 84:
            self.market_FCI = BrownianMotion(
                drift=self.market_inputs["SPY_drift"],
                std_dev=self.market_inputs["SPY_std"],
                n_steps=self.L + self.start + self.construction + 1,
                seed=self.sim,
            ).uncorrelated_GBM(self.final_capex[self.technology]["FCI"] * self.e)

        seed_val = self.sim if not deterministic else 0
        if not deterministic:
            self.NH3_market, self.NG_market = BrownianMotion(
                drift=self.market_inputs["NG_drift"],
                std_dev=self.market_inputs["NG_std"],
                correlation=0.8,
                n_steps=self.L + self.start + self.construction + 1,
                seed=self.sim,
            ).correlated_GBM([self.market_inputs["NH3_initial_price"], self.market_inputs["NG_initial_price"]])
        else:
            self.NH3_market = BrownianMotion(
                drift=self.market_inputs["NG_drift"],
                std_dev=self.market_inputs["NG_std"],
                n_steps=self.L + self.start + self.construction + 1,
                seed=0,
            ).uncorrelated_GBM(self.market_inputs["NH3_initial_price"])
            self.NG_market = BrownianMotion(
                drift=self.market_inputs["NG_drift"],
                std_dev=self.market_inputs["NG_std"],
                n_steps=self.L + self.start + self.construction + 1,
                seed=0,
            ).uncorrelated_GBM(self.market_inputs["NG_initial_price"])

        el_drift_idx = {"A": 1, "B": 0, "C": 0, "D": 0}
        if self.scenario in ["A", "B", "C"]:
            self.El_market = BrownianMotion(
                drift=self.market_inputs["El_drift"][el_drift_idx[self.scenario]],
                std_dev=self.market_inputs["El_STD"],
                n_steps=self.L + self.start + self.construction + 1,
                seed=seed_val,
            ).uncorrelated_GBM(self.market_inputs["El_initial_price"])
            if self.scenario == "C":
                self.El_PPA_market = 0
        if self.scenario == "D":
            self.El_PPA_market = self.market_inputs["PPA_pricing"][self.time][self.matching][self.policy]

        self.TCvalue = self.ira_credits["TCvalue"]
        self.income_tax = 0

        self.tax_credit_calculator = TaxCreditCalculator(
            self.technology, self.start, self.scenario, self.engineering_inputs,
            self.financial_inputs, self.carbon_intensity, self.ira_credits, self.final_capex,
            self.electrode_cost, self.battery_and_turbine_data_final, self.biomass_requirement,
            self.natural_gas_requirements, self.elec_inputs, self.aeo22_data, self.aeo23_data,
            self.capex_inputs,
        )
        self.emissions_of_technology = CarbonIntensity(
            self.technology, self.carbon_intensity, self.scenario, self.financial_inputs,
            self.engineering_inputs, self.biomass_requirement, self.natural_gas_requirements,
            self.elec_inputs, self.aeo22_data, self.aeo23_data,
        )
        self.baseline_emissions = CarbonIntensity(
            "AP SMR", self.carbon_intensity, self.scenario, self.financial_inputs,
            self.engineering_inputs, self.biomass_requirement, self.natural_gas_requirements,
            self.elec_inputs, self.aeo22_data, self.aeo23_data,
        )

        self.remaining_48C = 0
        self.remaining_48C_v1 = 0
        self.discount_factor = 1 + self.discount_rate / 12
        self.discount_factor_CAC = 1 + self.financial_inputs["CAC discount"] / 12
        self.inflation_correction = 1
        self.is_cbam = is_cbam

    # ------------------------------------------------------------------ #
    # Cash flow components
    # ------------------------------------------------------------------ #

    def calculate_FCI(self, T: int) -> float:
        opportunity_cost_adjustment = 0 if self.start == 0 else (self.market_FCI[self.start] - self.FCI * self.e)
        FCI_T = 0.0
        if self.start == 84 and T == self.start:
            tax_rate = (1 - self.phi_federal - self.phi_state) if opportunity_cost_adjustment > 0 else 1
            FCI_T += opportunity_cost_adjustment * tax_rate
        T_adj = T - self.start
        if 0 < T_adj <= 12:
            FCI_T += -self.Y[0] * self.FCI / 12
        elif 12 < T_adj <= 24:
            FCI_T += -self.Y[1] * self.FCI / 12
        elif 24 < T_adj <= 36:
            FCI_T += -self.Y[2] * self.FCI / 12
        return FCI_T

    def calculate_land(self, T: int) -> float:
        if T == self.start:
            return -self.land_cost
        if T == self.start + self.construction + self.L:
            return self.land_cost
        return 0.0

    def calculate_WC(self, T: int) -> float:
        if T == self.construction + self.start:
            return -self.WC
        if T == self.start + self.construction + self.L:
            return self.WC
        return 0.0

    def calculate_PMT(self, T: int) -> float:
        if 0 + self.start < T <= 12 + self.start:
            return -(self.r / 12) * (T - self.start) * (1 - self.e) * self.Y[0] * self.FCI / 12
        if 12 + self.start < T <= 24 + self.start:
            return -(self.r / 12) * (1 - self.e) * (
                (T - 12 - self.start) * self.Y[1] * self.FCI / 12 + self.Y[0] * self.FCI
            )
        if 24 + self.start < T <= 36 + self.start:
            return -(self.r / 12) * (1 - self.e) * (
                (T - 24 - self.start) * self.Y[2] * self.FCI / 12 + (self.Y[0] + self.Y[1]) * self.FCI
            )
        if 36 + self.start < T <= 36 + self.L_loan + self.start:
            return -self.FCI * (1 - self.e) * self.r / 12 / (1 - (1 + self.r / 12) ** (-12 * self.L_loan))
        return 0.0

    def calculate_Sales(self, T: int) -> float:
        if self.start + 36 < T <= self.start + self.construction + self.L:
            return self.M_NH3 * (self.F_A * self.H_operating / 24 / 12) * self.NH3_market[T]
        return 0.0

    def _ts_cost(self, T: int) -> float:
        if self.technology != "AP CCS":
            return 0.0
        baseline = CarbonIntensity(
            "AP SMR", self.carbon_intensity, self.scenario, self.financial_inputs,
            self.engineering_inputs, self.biomass_requirement, self.natural_gas_requirements,
            self.elec_inputs, self.aeo22_data, self.aeo23_data,
        ).total_emissions(T)
        return (
            abs(baseline - self.emissions_of_technology.total_emissions(T))
            * self.engineering_inputs["H2"] * 365 / 12
            * self.financial_inputs["availability"]
            * self.mi_opex_inputs["CCS T&S Cost"]
        )

    def _cbam_cost(self, T: int) -> float:
        if not self.is_cbam:
            return 0.0
        eu_ci_baseline = (
            self.carbon_intensity["EU 2023 emissions base"]
            * (1 - self.carbon_intensity["EU_emissions_reduction"]) ** (T / 12)
        )
        return (
            (eu_ci_baseline - self.emissions_of_technology.total_emissions(T))
            * self.engineering_inputs["H2"] * 365 / 12
            * self.financial_inputs["availability"]
            * self.ira_credits["EU_CO2_price"]
        )

    def calculate_OPEX(self, T: int) -> float:
        if not (self.start + 36 < T <= self.start + self.construction + self.L):
            return 0.0

        ts_cost = self._ts_cost(T)
        co2_tax = self._cbam_cost(T)
        constant_opex = self.final_mi_opex[self.technology]["MI_OPEX"] / 12
        mi_opex_counter = -(constant_opex + ts_cost) + co2_tax

        if T == self.start + self.construction + 1:
            mi_opex_counter -= self.final_mi_opex[self.technology]["MI_OPEX_start"]

        ng_cost = (self.natural_gas_requirements[self.technology] * self.NG_market[T]) / 12
        elec_cost = 0.0

        if self.scenario in ["A", "B"]:
            elec_cost = (self.elec_inputs[self.technology][1] * 1000 * self.H_operating / 12) * self.El_market[T]
        elif self.scenario == "D":
            elec_cost = self.elec_inputs[self.technology][1] * self.El_PPA_market * 1000 * self.H_operating / 12
        elif self.scenario == "C" and self.technology != "AP SMR":
            wind_capacity = self.capex_inputs["wind_capacity"][self.technology] * 1000
            battery_capacity = self.capex_inputs["battery_capacity"][self.technology] * 1000 / 4
            solar_capacity = self.capex_inputs["solar_capacity"][self.technology] * 1000
            tau = T % 12
            battery_discharge = self.elec_inputs["discharge"][self.technology][tau]
            wind_opex = self.mi_opex_inputs["Wind OPEX"] * wind_capacity / 12
            battery_fixed_opex = self.mi_opex_inputs["Battery OPEX"] * battery_capacity / 12
            battery_var_opex = self.mi_opex_inputs["Battery Var OPEX"] * battery_discharge / 4
            solar_opex = self.mi_opex_inputs["Solar OPEX"] * solar_capacity / 12
            opex = wind_opex + battery_fixed_opex + battery_var_opex + solar_opex
            ppa_price = self.market_inputs["PPA_pricing_for_C"][self.time][self.policy]
            electricity_sold = self.elec_inputs["curtailment"][self.technology][tau] * max(self.El_market[T], ppa_price)
            elec_cost = -electricity_sold + opex

        md_opex = mi_opex_counter - (ng_cost + elec_cost)
        dist_mkt = self.mi_opex_inputs["distribution_and_marketing"]
        md_opex += md_opex * (dist_mkt + dist_mkt * self.mi_opex_inputs["R&D costs"])
        return md_opex

    def calculate_Depreciation(self, T: int) -> float:
        if self.start + self.construction <= T <= 36 + self.L_equipment:
            return -(1 / self.L_equipment) * self.C_equipment
        return 0.0

    def _replacement_cost_for_component(self, time_diff: int, lifetime: int, capex_key: str) -> float:
        if time_diff % (lifetime * 12) != 0:
            return 0.0
        wind_cap = self.capex_inputs["wind_capacity"][self.technology] * 1000
        battery_cap = self.capex_inputs["battery_capacity"][self.technology] * 1000 / 4
        solar_cap = self.capex_inputs["solar_capacity"][self.technology] * 1000
        cost = self.capex_inputs[f"{capex_key} {self.time}"]
        if capex_key == "Battery Storage CAPEX":
            return battery_cap * cost
        if capex_key == "Wind Turbine CAPEX":
            return wind_cap * cost
        if capex_key == "Solar PV CAPEX":
            return solar_cap * cost
        return 0.0

    def stack_replacement_costs(self, T: int) -> float:
        cost_counter = 0.0
        lifetime_counter = T - self.start - self.construction
        operating = T > self.start + self.construction

        if self.scenario != "C":
            if (
                self.technology == "AP AEC"
                and operating
                and lifetime_counter % self.capex_inputs["AEC stack lifetime"] == 0
            ):
                cost_counter += (
                    self.electrode_cost
                    * self.capex_inputs["Stack and battery replacement"]
                    / self.capex_inputs["CAPEX_from_installed_cost"]
                )
            return -cost_counter

        if lifetime_counter > 0 and self.technology != "AP SMR":
            cost_counter += self._replacement_cost_for_component(
                lifetime_counter, self.capex_inputs["Battery lifetime"], "Battery Storage CAPEX"
            )
            cost_counter += self._replacement_cost_for_component(
                lifetime_counter, self.capex_inputs["Wind farm lifetime"], "Wind turbine CAPEX"
            )
            cost_counter += self._replacement_cost_for_component(
                lifetime_counter, self.capex_inputs["Wind farm lifetime"], "Solar PV CAPEX"
            )
        if (
            self.technology == "AP AEC"
            and operating
            and lifetime_counter % self.capex_inputs["AEC stack lifetime"] == 0
        ):
            cost_counter += (
                self.electrode_cost
                * self.capex_inputs["Stack and battery replacement"]
                / self.capex_inputs["CAPEX_from_installed_cost"]
            )
        return -cost_counter

    def calculate_Tax(self, T: int) -> float:
        self.income_tax = 0.0
        if self.start + self.construction < T < self.start + self.construction + self.L:
            net_revenue = (
                self.calculate_Depreciation(T)
                + self.calculate_OPEX(T)
                + self.calculate_Sales(T)
                + self.calculate_PMT(T)
                + self.stack_replacement_costs(T)
            )
            if net_revenue > 0:
                self.income_tax = -net_revenue * (self.phi_state + self.phi_federal)
        return self.income_tax

    # ------------------------------------------------------------------ #
    # Tax credit helpers
    # ------------------------------------------------------------------ #

    def _tc_value_helper(self, T: int, credit_45y: bool = False) -> float:
        rel = T - (self.start + self.construction)
        if rel <= 0:
            return 0.0
        if rel <= 5 * 12:
            return self.TCvalue["Year 6"] if credit_45y else self.TCvalue["Year 1-5"]
        if rel <= 6 * 12:
            return self.TCvalue["Year 6"]
        if rel <= 7 * 12:
            return self.TCvalue["Year 7"]
        if rel <= 8 * 12:
            return self.TCvalue["Year 8"]
        if rel <= 9 * 12:
            return self.TCvalue["Year 9"]
        return self.TCvalue["Year 10 and after"]

    def _tc_converter(
        self, income_tax: float, tax_credit: float, T: int,
        is45y: bool = False, set_value: bool = False, value=None
    ) -> tuple[float, float]:
        tc_market_value = value if set_value else self._tc_value_helper(T, credit_45y=is45y)
        if tax_credit - income_tax < 0:
            return tax_credit, income_tax - tax_credit
        cash_eq = income_tax + (tax_credit - income_tax) * tc_market_value
        return cash_eq, 0.0

    def _choose_policy(
        self, compare45v_45q: bool = False, compare45y_48e: bool = False,
        set_value: bool = False, value=None
    ) -> bool:
        c1, c2 = 0.0, 0.0
        for T in range(self.start + self.construction + self.L):
            if compare45v_45q:
                c1 += self.tax_credit_calculator.calculate_45V(T) / self.discount_factor ** (T - self.start)
                c2 += self.tax_credit_calculator.calculate_45Q(T) / self.discount_factor ** (T - self.start)
            elif compare45y_48e:
                income_tax = abs(self.calculate_Tax(T))
                if T == self.start + self.construction + 1:
                    c1 += self.tax_credit_calculator.calculate_48E(T) / self.discount_factor ** (T - self.start)
                ce_45y, _ = self._tc_converter(income_tax, self.tax_credit_calculator.calculate_45Y(T), T,
                                               set_value=set_value, value=value)
                c2 += ce_45y / self.discount_factor ** (T - self.start)
        return c1 > c2

    def _find_abated_emissions(self) -> float:
        total = 0.0
        for T in range(self.start + self.construction, self.start + self.construction + self.L):
            diff = (
                self.baseline_emissions.total_emissions(T) - self.emissions_of_technology.total_emissions(T)
            )
            monthly_h2 = self.engineering_inputs["H2"] * 365 / 12 * self.financial_inputs["availability"]
            total += diff * monthly_h2 / (self.discount_factor_CAC ** (T - self.start))
        return total

    def _find_hydrogen_produced(self, discount_factor: float) -> float:
        h2_kgpm = (
            self.engineering_inputs["H2"] * self.F_A * 365 / 12 * 1000
        )
        total = 0.0
        for T in range(self.start + self.construction, self.start + self.construction + 10 * 12):
            total += h2_kgpm / (discount_factor ** (T - self.start))
        return total

    # ------------------------------------------------------------------ #
    # Policy selection & cash-equivalent credits
    # ------------------------------------------------------------------ #

    def cash_equivalent_credits(self, T: int) -> float:
        if not self.policy or self.technology == "AP SMR":
            return 0.0
        if self.technology == "AP CCS" and T == 0:
            self.is45V = self._choose_policy(compare45v_45q=True)
        if self.scenario == "C" and T == 0:
            self.is48E = self._choose_policy(compare45y_48e=True)

        if self.technology in ["AP BH2S", "AP AEC"]:
            credits_ptc = self.tax_credit_calculator.calculate_45V(T)
        elif self.technology == "AP CCS":
            credits_ptc = (
                self.tax_credit_calculator.calculate_45V(T)
                if self.is45V
                else self.tax_credit_calculator.calculate_45Q(T)
            )
        else:
            credits_ptc = 0.0

        credits_48c = 0.0
        if self.is48E:
            credits_48e = self.tax_credit_calculator.calculate_48E(T) if T == self.start + self.construction + 1 else 0.0
            credits_45y = 0.0
        else:
            credits_48e = 0.0
            credits_45y = self.tax_credit_calculator.calculate_45Y(T)

        income_tax = abs(self.calculate_Tax(T))
        credits_48c, income_tax = self._tc_converter(income_tax, credits_48c, T)
        credits_48e, income_tax = self._tc_converter(income_tax, credits_48e, T)
        credits_45y, income_tax = self._tc_converter(income_tax, credits_45y, T, is45y=True)
        credits_ptc, income_tax = self._tc_converter(income_tax, credits_ptc, T)

        return credits_ptc + credits_45y + credits_48e + credits_48c

    def _nominal_tax_credits(self, T: int, separate: bool = False):
        if not self.policy or self.technology == "AP SMR":
            return 0.0 if not separate else {"45V": 0.0, "45Q": 0.0, "48E": 0.0, "45Y": 0.0}
        if self.technology == "AP CCS" and T == 0:
            self.is45V = self._choose_policy(compare45v_45q=True)
        elif self.technology != "AP CCS":
            self.is45V = True
        if self.scenario == "C" and T == 0:
            self.is48E = self._choose_policy(compare45y_48e=True)

        credits = {
            "45V": self.tax_credit_calculator.calculate_45V(T) if self.is45V else 0.0,
            "45Q": self.tax_credit_calculator.calculate_45Q(T) if not self.is45V else 0.0,
            "48E": self.tax_credit_calculator.calculate_48E(T) if (T == self.start + self.construction + 1 and self.is48E) else 0.0,
            "45Y": self.tax_credit_calculator.calculate_45Y(T) if not self.is48E else 0.0,
        }
        return credits if separate else sum(credits.values())

    def _convert_nominal_to_CE(self, T: int, separate: bool = False):
        credits = self._nominal_tax_credits(T, separate=True)
        income_tax = abs(self.calculate_Tax(T))
        ce = {}
        for key, val in credits.items():
            is45y = key == "45Y"
            ce[key], income_tax = self._tc_converter(income_tax, val, T, is45y=is45y)
        return ce if separate else sum(ce.values())

    # ------------------------------------------------------------------ #
    # Primary outputs
    # ------------------------------------------------------------------ #

    def calculate_CF(self, T: int) -> float:
        return (
            self.calculate_FCI(T)
            + self.calculate_land(T)
            + self.calculate_WC(T)
            + self.calculate_PMT(T)
            + self.calculate_Sales(T)
            + self.calculate_OPEX(T)
            + self.calculate_Tax(T)
            + self.cash_equivalent_credits(T)
            + self.stack_replacement_costs(T)
        )

    def calculate_NPV(self, roi: bool = False) -> float:
        npv = 0.0
        roi_value = 0.0
        for T in range(self.start + self.construction + self.L + 1):
            cf = self.calculate_CF(T)
            capex_t = self.calculate_FCI(T) + self.calculate_land(T) + self.calculate_WC(T)
            if not roi:
                npv += cf / self.discount_factor ** (T - self.start)
            else:
                roi_value += (cf - capex_t) / self.discount_factor ** (T - self.start)

        npv /= self.M_NH3 * 365 * self.L / 12 * self.F_A
        npv /= self.inflation_correction
        roi_value /= self.final_capex[self.technology]["CAPEX"]
        roi_value /= self.inflation_correction
        return npv if not roi else roi_value

    def CAC_updated(self) -> float:
        carbon_abated = self._find_abated_emissions()
        cac = 0.0
        for T in range(self.start + self.construction + self.L + 1):
            cac += (self._nominal_tax_credits(T) / carbon_abated) / (self.discount_factor_CAC ** (T - self.start))
        return cac

    def total_support(self) -> float:
        h2 = self._find_hydrogen_produced(self.discount_factor_CAC)
        total = 0.0
        for T in range(self.start + self.construction + self.L + 1):
            total += (self._nominal_tax_credits(T) / h2) / (self.discount_factor_CAC ** (T - self.start))
        return total

    def total_CE_support(self) -> float:
        h2 = self._find_hydrogen_produced(self.discount_factor)
        total = 0.0
        for T in range(self.start + self.construction + self.L + 1):
            total += (self._convert_nominal_to_CE(T) / h2) / (self.discount_factor ** (T - self.start))
        return total

    def total_CE_support_social(self) -> float:
        h2 = self._find_hydrogen_produced(self.discount_factor_CAC)
        total = 0.0
        for T in range(self.start + self.construction + self.L + 1):
            total += (self._convert_nominal_to_CE(T) / h2) / (self.discount_factor_CAC ** (T - self.start))
        return total

    def separate_total_support(self) -> dict:
        h2 = self._find_hydrogen_produced(self.discount_factor_CAC)
        totals = {"45V": 0.0, "45Q": 0.0, "48E": 0.0, "45Y": 0.0}
        for T in range(self.start + self.construction + self.L + 1):
            per_credit = self._nominal_tax_credits(T, separate=True)
            for key, val in per_credit.items():
                totals[key] += (val / h2) / (self.discount_factor_CAC ** (T - self.start))
        return totals

    def carbon_abatement_cost(
        self, value=None, set_value: bool = False, absolute: bool = False,
        separate: bool = False, quality_assure: bool = False
    ):
        denominator = 1 if absolute else self._find_abated_emissions()

        def _ce_for_cac(T: int):
            if not self.policy or self.technology == "AP SMR":
                return (0.0, 0.0, 0.0, 0.0, 0.0) if separate else 0.0

            if self.technology == "AP CCS" and T == 0:
                self.is45V = self._choose_policy(compare45v_45q=True)
            if self.scenario == "C" and T == 0:
                self.is48E = self._choose_policy(compare45y_48e=True)

            if self.technology in ["AP BH2S", "AP AEC"]:
                credits_ptc = self.tax_credit_calculator.calculate_45V(T)
            elif self.technology == "AP CCS":
                credits_ptc = (
                    self.tax_credit_calculator.calculate_45V(T) if self.is45V
                    else self.tax_credit_calculator.calculate_45Q(T)
                )
            else:
                credits_ptc = 0.0

            credits_48c = 0.0
            if self.is48E:
                credits_48e = self.tax_credit_calculator.calculate_48E(T) if T == self.start + self.construction + 1 else 0.0
                credits_45y = 0.0
            else:
                credits_48e = 0.0
                credits_45y = self.tax_credit_calculator.calculate_45Y(T)

            income_tax = abs(self.calculate_Tax(T))
            credits_48c, income_tax = self._tc_converter(income_tax, credits_48c, T, set_value=set_value, value=value)
            credits_48e, income_tax = self._tc_converter(income_tax, credits_48e, T, set_value=set_value, value=value)
            credits_45y, income_tax = self._tc_converter(income_tax, credits_45y, T, is45y=True, set_value=set_value, value=value)

            ce_45v, ce_45q = 0.0, 0.0
            if self.is45V and self.technology == "AP CCS":
                ce_45v, income_tax = self._tc_converter(income_tax, credits_ptc, T, set_value=set_value, value=value)
            elif not self.is45V and self.technology == "AP CCS":
                ce_45q, income_tax = self._tc_converter(income_tax, credits_ptc, T, set_value=set_value, value=value)
            else:
                ce_45v, income_tax = self._tc_converter(income_tax, credits_ptc, T, set_value=set_value, value=value)

            if separate:
                return ce_45v, ce_45q, credits_45y, credits_48c, credits_48e
            return ce_45v + ce_45q + credits_45y + credits_48c + credits_48e

        store = {"T": [], "45V": [], "45Q": [], "45Y": [], "48C": [], "48E": []}
        cac = cac_45v = cac_45q = cac_45y = cac_48c = cac_48e = 0.0

        for T in range(self.start + self.construction + self.L + 1):
            if separate:
                v, q, y, c, e = _ce_for_cac(T)
                store["T"].append(T)
                store["45V"].append(v / denominator)
                store["45Q"].append(q / denominator)
                store["45Y"].append(y / denominator)
                store["48C"].append(c / denominator)
                store["48E"].append(e / denominator)
                df = 1 / self.discount_factor ** (T - self.start)
                cac_45v += df * v / denominator
                cac_45q += df * q / denominator
                cac_45y += df * y / denominator
                cac_48c += df * c / denominator
                cac_48e += df * e / denominator
            else:
                all_cash = _ce_for_cac(T) / (self.discount_factor_CAC ** (T - self.start))
                cac += all_cash / denominator

        if separate and quality_assure:
            return pd.DataFrame(store)
        if separate:
            return cac_45v, cac_45q, cac_45y, cac_48c, cac_48e
        cac /= self.inflation_correction
        return cac

    def quality_assure(self) -> pd.DataFrame:
        data = pd.DataFrame(
            columns=["time", "FCI", "Land", "WC", "PMT", "Sales", "OPEX", "Tax", "Credits", "Stack_replacement", "Cash Flow"]
        )
        for T in range(self.start + self.construction + self.L + 1):
            data.loc[len(data)] = [
                T,
                self.calculate_FCI(T),
                self.calculate_land(T),
                self.calculate_WC(T),
                self.calculate_PMT(T),
                self.calculate_Sales(T),
                self.calculate_OPEX(T),
                self.calculate_Tax(T),
                self.cash_equivalent_credits(T),
                self.stack_replacement_costs(T),
                self.calculate_CF(T),
            ]
        return data
