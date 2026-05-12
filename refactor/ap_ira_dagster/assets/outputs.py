"""Downstream assets: merge all partition results and export to Excel."""

from pathlib import Path

import pandas as pd
from dagster import AllPartitionMapping, AssetExecutionContext, AssetIn, asset

from ap_ira_lib.io.excel import dataframes_to_excel, get_current_est_time

from ..config import ExportConfig

_SHEETS = ["NPV", "NPV_no_policy", "CAC", "CI", "TaxCredits"]


@asset(
    ins={
        "simulation_results": AssetIn(
            partition_mapping=AllPartitionMapping(),
        )
    },
    group_name="outputs",
    description=(
        "Concatenate every (scenario × time_horizon) partition into one DataFrame per "
        "output sheet (NPV, CAC, CI, TaxCredits). Requires all 8 partitions to be "
        "materialized upstream."
    ),
)
def merged_results(
    context: AssetExecutionContext,
    simulation_results: dict[str, dict[str, pd.DataFrame]],
) -> dict[str, pd.DataFrame]:
    """Merge all partition DataFrames into unified result tables."""
    buckets: dict[str, list[pd.DataFrame]] = {sheet: [] for sheet in _SHEETS}

    for partition_key, partition_dfs in simulation_results.items():
        for sheet in _SHEETS:
            if sheet in partition_dfs:
                buckets[sheet].append(partition_dfs[sheet])
        context.log.debug(f"Merged partition: {partition_key}")

    result = {
        sheet: pd.concat(frames, ignore_index=True) for sheet, frames in buckets.items() if frames
    }

    for sheet, df in result.items():
        context.log.info(f"  {sheet}: {len(df):,} rows")

    return result


@asset(
    group_name="outputs",
    description=(
        "Write the merged simulation results to a timestamped Excel file under results/. "
        "Set ExportConfig.output_filename to pin the filename."
    ),
)
def excel_output(
    context: AssetExecutionContext,
    config: ExportConfig,
    merged_results: dict[str, pd.DataFrame],
) -> str:
    """Export merged DataFrames to Excel; return the output file path."""
    output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)

    if config.output_filename:
        output_path = output_dir / config.output_filename
    else:
        timestamp = get_current_est_time().replace(":", "-").replace(" ", "_")
        output_path = output_dir / f"{timestamp}_results.xlsx"

    dataframes_to_excel(merged_results, output_path)
    context.log.info(f"Results written to {output_path}")
    return str(output_path)
