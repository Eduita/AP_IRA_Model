"""Tests for CAPEX calculation."""

import pytest

from ap_ira_lib.core.capex import CAPEX

# Minimal but realistic fixture data
_CAPEX_INPUTS = {
    "Land Cost": 100_000,
    "Instrumentation and Controls Cost": 0.18,
    "Piping Cost": 0.20,
    "Electrical Cost": 0.10,
    "Buildings Cost": 0.05,
    "Service Facilities and Yard Improvements Cost": 0.10,
    "Engineering and Supervision Cost": 0.20,
    "Legal Expenses Cost": 0.04,
    "Construction Expense and Contractors Fee Cost": 0.10,
    "Contingency Cost": 0.15,
    "Working Capital": 0.05,
}

_BASIC_EQ = {
    "AP SMR": [10_000_000, 8_000_000],  # [installed, uninstalled]
    "AP AEC": [15_000_000, 12_000_000],
}


@pytest.fixture
def built_capex():
    c = CAPEX(_CAPEX_INPUTS)
    c.get_installed_and_uninstalled_cost(_BASIC_EQ, "AP SMR")
    c.calculate_fci_capex_and_wc()
    return c


# ── get_installed_and_uninstalled_cost ────────────────────────────────────────


def test_get_installed_and_uninstalled_cost_values():
    c = CAPEX(_CAPEX_INPUTS)
    result = c.get_installed_and_uninstalled_cost(_BASIC_EQ, "AP SMR")
    assert result["installed costs"] == 10_000_000
    assert result["uninstalled cost"] == 8_000_000


def test_get_installed_and_uninstalled_cost_sets_attributes():
    c = CAPEX(_CAPEX_INPUTS)
    c.get_installed_and_uninstalled_cost(_BASIC_EQ, "AP AEC")
    assert c.installed_costs == 15_000_000
    assert c.uninstalled_cost == 12_000_000


# ── calculate_fci_capex_and_wc ────────────────────────────────────────────────


def test_calculate_fci_capex_and_wc_return_keys(built_capex):
    c = CAPEX(_CAPEX_INPUTS)
    c.get_installed_and_uninstalled_cost(_BASIC_EQ, "AP SMR")
    result = c.calculate_fci_capex_and_wc()
    assert set(result.keys()) == {"UC", "FCI", "WC", "CAPEX"}


def test_fci_positive(built_capex):
    assert built_capex.FCI > 0


def test_wc_positive(built_capex):
    assert built_capex.WC > 0


def test_capex_equals_fci_plus_wc(built_capex):
    assert abs(built_capex.CAPEX - (built_capex.FCI + built_capex.WC)) < 1.0


def test_capex_greater_than_fci(built_capex):
    assert built_capex.CAPEX > built_capex.FCI


def test_uc_equals_uninstalled_cost(built_capex):
    assert built_capex.UC == built_capex.uninstalled_cost


# ── add_cost_outside_of_equipment_list ───────────────────────────────────────


def test_add_cost_increases_capex(built_capex):
    original = built_capex.CAPEX
    built_capex.add_cost_outside_of_equipment_list(500_000)
    assert built_capex.CAPEX > original


def test_add_cost_return_keys(built_capex):
    result = built_capex.add_cost_outside_of_equipment_list(100_000)
    assert set(result.keys()) == {"UC", "FCI", "WC", "CAPEX"}


# ── as_dict ───────────────────────────────────────────────────────────────────


def test_as_dict_contains_required_keys(built_capex):
    d = built_capex.as_dict()
    for key in ("UC", "FCI", "WC", "CAPEX", "land", "installation"):
        assert key in d, f"Missing key: {key}"


def test_as_dict_values_consistent_with_attributes(built_capex):
    d = built_capex.as_dict()
    assert d["FCI"] == built_capex.FCI
    assert d["WC"] == built_capex.WC
    assert d["CAPEX"] == built_capex.CAPEX
