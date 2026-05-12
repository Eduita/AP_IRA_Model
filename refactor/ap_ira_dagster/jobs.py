"""Job definitions for the AP IRA Dagster pipeline.

Two jobs:

- ``simulation_job``   — run Monte Carlo for all scenario×horizon partitions in parallel.
- ``aggregation_job``  — merge all partition results and export to Excel.

Typical workflow
----------------
1. Launch ``simulation_job`` (Dagster will parallelise across 8 partitions).
2. Once all partitions are green, launch ``aggregation_job``.

Or trigger the ``on_all_partitions_materialized`` automation condition on
``merged_results`` to run aggregation automatically.
"""

from dagster import AssetSelection, define_asset_job

from .partitions import scenario_horizon_partitions

simulation_job = define_asset_job(
    name="simulation_job",
    selection=AssetSelection.groups("simulation"),
    partitions_def=scenario_horizon_partitions,
    description=(
        "Run Monte Carlo simulations for every (scenario × time_horizon) partition. "
        "Each of the 8 partitions can execute in parallel on separate workers."
    ),
)

aggregation_job = define_asset_job(
    name="aggregation_job",
    selection=AssetSelection.groups("outputs"),
    description=(
        "Merge all 8 partition results into unified DataFrames and export to Excel. "
        "Run this after all simulation_job partitions have succeeded."
    ),
)
