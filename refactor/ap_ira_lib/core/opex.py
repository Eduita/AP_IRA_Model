"""Maintenance and indirect OPEX (MI_OPEX) for ammonia production technologies."""


class MIOPEX:
    def __init__(
        self,
        processing_steps: int,
        hourly_pay_per_operator: float,
        heuristics_factors: dict,
        technology: str,
        financial_inputs: dict,
        mi_opex_inputs: dict,
        final_capex: dict,
        hp_steam_requirements: dict,
        bfw_requirements: dict,
        biomass_price: float,
        biomass_requirement: float,
        capex_inputs: dict,
    ):
        self.processing_steps = processing_steps
        self.hourly_pay_per_operator = hourly_pay_per_operator
        self.heuristics_factors = heuristics_factors
        self.technology = technology
        self.financial_inputs = financial_inputs
        self.mi_opex_inputs = mi_opex_inputs
        self.final_capex = final_capex
        self.hp_steam_requirements = hp_steam_requirements
        self.bfw_requirements = bfw_requirements
        self.biomass_price = biomass_price
        self.biomass_requirement = biomass_requirement
        self.capex_inputs = capex_inputs

        self.total_labor_costs = None
        self.operating_labor = None
        self.maintenance = None

    def calculate_labor_costs(self) -> float:
        operators_per_day = (
            self.mi_opex_inputs["hours_perday_perprocessingstep"] * self.processing_steps / 8
        )
        operator_shifts_per_week = operators_per_day * 7
        operators = operator_shifts_per_week / 5
        wage_per_week_per_operator = 40 * self.hourly_pay_per_operator
        annual_cost_of_labor = (
            wage_per_week_per_operator * operators * 52 * self.financial_inputs["availability"]
        )

        supervision = annual_cost_of_labor * self.heuristics_factors["supervision"]
        maintenance = (
            self.final_capex[self.technology]["FCI"] * self.heuristics_factors["maintenance"]
        )
        self.maintenance = maintenance
        operating_supplies = maintenance * self.heuristics_factors["operating_supplies"]
        laboratory_charges = annual_cost_of_labor * self.heuristics_factors["laboratory_charges"]
        patents_and_royalties = (
            self.final_capex[self.technology]["CAPEX"]
            * self.heuristics_factors["patents_and_royalties"]
        )
        overhead_costs = (
            annual_cost_of_labor + supervision + maintenance
        ) * self.heuristics_factors["overhead"]
        self.operating_labor = annual_cost_of_labor
        self.total_labor_costs = (
            annual_cost_of_labor
            + supervision
            + maintenance
            + operating_supplies
            + laboratory_charges
            + patents_and_royalties
            + overhead_costs
        )
        return self.total_labor_costs

    def fixed_charges(self) -> float:
        financing = (
            self.mi_opex_inputs["fixed_charges"]["Financing Costs"]
            * self.final_capex[self.technology]["CAPEX"]
        )
        rent = self.mi_opex_inputs["fixed_charges"]["Rent"] * self.capex_inputs["Land Cost"]
        insurance = (
            self.mi_opex_inputs["fixed_charges"]["Insurance"]
            * self.final_capex[self.technology]["FCI"]
        )
        local_property_taxes = (
            self.mi_opex_inputs["fixed_charges"]["Local Property Taxes"]
            * self.final_capex[self.technology]["FCI"]
        )
        administrative_costs = (
            self.mi_opex_inputs["fixed_charges"]["Administrative Costs"] * self.operating_labor
        )
        return financing + rent + insurance + local_property_taxes + administrative_costs

    def get_start_up_costs(self) -> float:
        return self.mi_opex_inputs["start-up costs"][self.technology]

    def misc_up_costs(self) -> float:
        return self.mi_opex_inputs["misc_raw_materials"][self.technology]

    def utilities_costs(self) -> float:
        if self.technology in ["AP SMR", "AP CCS"]:
            return self.bfw_requirements[self.technology] * self.mi_opex_inputs["BFW cost"]
        elif self.technology == "AP AEC":
            return (
                self.bfw_requirements[self.technology] * self.mi_opex_inputs["BFW cost"]
                + self.bfw_requirements["AP AEC osmosis"]
                * self.mi_opex_inputs["AEC BFW cost reverse osmosis"]
            )
        else:
            return (
                self.bfw_requirements[self.technology] * self.mi_opex_inputs["BFW cost"]
                + self.biomass_price * self.biomass_requirement
            )
