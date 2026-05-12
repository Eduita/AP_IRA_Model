"""Dagster run-config classes for the AP IRA pipeline.

All fields mirror the ``simulation`` block of ap_ira.yaml and can be
overridden per-run from the Dagster UI or via RunConfig in code.
"""

from dagster import Config


class SimulationRunConfig(Config):
    """Monte Carlo simulation parameters — override to run faster / change physics."""

    n_simulations: int = 400
    matching: str = "monthly"   # yearly | monthly | hourly
    cbam: bool = False
    L: int = 480                # plant lifetime, months (40 years)


class ExportConfig(Config):
    """Excel export settings for the excel_output asset."""

    output_filename: str = ""   # empty → timestamped filename
