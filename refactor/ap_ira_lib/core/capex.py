"""CAPEX calculation for ammonia production technologies."""


class CAPEX:
    def __init__(self, inputs: dict):
        self.inputs = inputs
        self.installed_costs = None
        self.uninstalled_cost = None
        self.CAPEX = None
        self.WC = None
        self.FCI = None
        self.UC = None
        self.IC = None

        # Direct cost components
        self.installation = None
        self.instrumentation_and_controls = None
        self.piping = None
        self.electrical = None
        self.building_process_auxiliary = None
        self.service_facilities_and_yard_improvements = None
        self.land = self.inputs["Land Cost"]

        # Indirect cost components
        self.engineering_supervision = None
        self.legal_expenses = None
        self.construction_expense_and_contractors_fee = None
        self.contingency = None

    def get_installed_and_uninstalled_cost(
        self, basic_equipment_costs: dict, technology: str
    ) -> dict:
        self.installed_costs = basic_equipment_costs[technology][0]
        self.uninstalled_cost = basic_equipment_costs[technology][1]
        return {"installed costs": self.installed_costs, "uninstalled cost": self.uninstalled_cost}

    def calculate_fci_capex_and_wc(self) -> dict:
        self.UC = self.uninstalled_cost
        self.IC = self.installed_costs
        purchased_equipment_factor = self.UC * (1 / ((2717 / 100) ** 0.6))

        self.installation = self.UC + (-self.UC + self.IC)
        self.instrumentation_and_controls = (
            self.inputs["Instrumentation and Controls Cost"] * purchased_equipment_factor
        )
        self.piping = self.inputs["Piping Cost"] * purchased_equipment_factor
        self.electrical = self.inputs["Electrical Cost"] * purchased_equipment_factor
        self.building_process_auxiliary = self.inputs["Buildings Cost"] * purchased_equipment_factor
        self.service_facilities_and_yard_improvements = (
            self.inputs["Service Facilities and Yard Improvements Cost"]
            * purchased_equipment_factor
        )
        direct_costs = (
            self.instrumentation_and_controls
            + self.piping
            + self.electrical
            + self.building_process_auxiliary
            + self.service_facilities_and_yard_improvements
            + self.land
            + self.installation
        )

        self.engineering_supervision = (
            self.inputs["Engineering and Supervision Cost"] * purchased_equipment_factor
        )
        self.legal_expenses = self.inputs["Legal Expenses Cost"] * purchased_equipment_factor
        self.construction_expense_and_contractors_fee = (
            self.inputs["Construction Expense and Contractors Fee Cost"]
            * purchased_equipment_factor
        )
        self.contingency = self.inputs["Contingency Cost"] * purchased_equipment_factor
        indirect_costs = (
            self.engineering_supervision
            + self.legal_expenses
            + self.construction_expense_and_contractors_fee
            + self.contingency
        )

        self.FCI = direct_costs + indirect_costs
        self.WC = self.inputs["Working Capital"] * self.FCI * (1 / ((2717 / 100) ** 0.6))
        self.CAPEX = self.FCI + self.WC
        return {"UC": self.UC, "FCI": self.FCI, "WC": self.WC, "CAPEX": self.CAPEX}

    def add_cost_outside_of_equipment_list(self, additional_cost: float) -> dict:
        copy = self.CAPEX
        self.CAPEX += additional_cost
        ratio = 1 / (copy / additional_cost)

        self.WC += ratio * self.WC
        self.FCI += ratio * self.FCI
        self.UC += ratio * self.UC
        self.installation += ratio * self.installation
        self.instrumentation_and_controls += ratio * self.instrumentation_and_controls
        self.piping += ratio * self.piping
        self.electrical += ratio * self.electrical
        self.building_process_auxiliary += ratio * self.building_process_auxiliary
        self.service_facilities_and_yard_improvements += (
            ratio * self.service_facilities_and_yard_improvements
        )
        self.engineering_supervision += ratio * self.engineering_supervision
        self.legal_expenses += ratio * self.legal_expenses
        self.construction_expense_and_contractors_fee += (
            ratio * self.construction_expense_and_contractors_fee
        )
        self.contingency += ratio * self.contingency

        return {"UC": self.UC, "FCI": self.FCI, "WC": self.WC, "CAPEX": self.CAPEX}

    def as_dict(self) -> dict:
        return {
            "UC": self.UC,
            "FCI": self.FCI,
            "WC": self.WC,
            "CAPEX": self.CAPEX,
            "installation": self.installation,
            "instrumentation_and_controls": self.instrumentation_and_controls,
            "piping": self.piping,
            "electrical": self.electrical,
            "building_process_auxiliary": self.building_process_auxiliary,
            "service_facilities_and_yard_improvements": self.service_facilities_and_yard_improvements,
            "land": self.land,
            "engineering_supervision": self.engineering_supervision,
            "legal_expenses": self.legal_expenses,
            "construction_expense_and_contractors_fee": self.construction_expense_and_contractors_fee,
            "contingency": self.contingency,
        }
