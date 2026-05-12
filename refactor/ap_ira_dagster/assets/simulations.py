"""Partitioned asset: run Monte Carlo simulations for one (scenario × time) slice."""

import numpy as np
import pandas as pd
from dagster import AssetExecutionContext, asset

from ap_ira_lib.pipeline.base import SimContext
from ap_ira_lib.pipeline.runner import _build_pipeline

from ..config import SimulationRunConfig
from ..partitions import parse_partition_key, scenario_horizon_partitions
from ..resources import ModelConfigResource

_CI_YEARS = [str(2023 + i) for i in range(28)]
_CI_MONTHS = [12 * i for i in range(28)]


@asset(
    partitions_def=scenario_horizon_partitions,
    group_name="simulation",
    description=(
        "Monte Carlo simulation results for one (scenario × time_horizon) partition. "
        "Returns NPV, NPV_no_policy, CAC, CI, and TaxCredits DataFrames."
    ),
)
def simulation_results(
    context: AssetExecutionContext,
    config: SimulationRunConfig,
    model_config: ModelConfigResource,
) -> dict[str, pd.DataFrame]:
    """Run ``config.n_simulations`` draws for this partition and return result DataFrames."""
    scenario, time = parse_partition_key(context.partition_key)

    cfg = model_config.load()

    # Pluck resolved dimensions from the config.
    technologies: list[str] = cfg["technologies"]
    time_horizons: list[int] = cfg["time_horizons"]
    start_month = (time - time_horizons[0]) * 12

    matching = config.matching
    is_cbam = config.cbam
    L = config.L
    n_sims = config.n_simulations

    # Build the stage pipeline once; stages cache any expensive I/O internally.
    pipeline = _build_pipeline(cfg)

    aeo_path = cfg["data"]["aeo_energy_mix"]
    aeo22 = pd.read_excel(aeo_path, sheet_name="AEO22", index_col=0)
    aeo23 = pd.read_excel(aeo_path, sheet_name="AEO23", index_col=0)

    non_smr = [t for t in technologies if t != "AP SMR"]
    tech_cols = [t.replace(" ", "_") for t in technologies]
    non_smr_cols = [t.replace(" ", "_") for t in non_smr]

    npv_rows: list = []
    npv_np_rows: list = []
    cac_rows: list = []
    ci_rows: list = []
    tc_rows: list = []

    context.log.info(
        f"Starting {n_sims} simulations — scenario={scenario}, time={time}, matching={matching}"
    )

    for sim in range(n_sims):
        np.random.seed(sim)

        ctx = SimContext(
            scenario=scenario,
            start_month=start_month,
            time=time,
            sim_index=sim,
            matching=matching,
            technologies=technologies,
            L=L,
            policy=True,
            is_cbam=is_cbam,
            data={"aeo22_data": aeo22, "aeo23_data": aeo23},
        )

        ctx = pipeline.run(ctx)
        results = ctx.data.get("dcf_results", {})
        meta = (time, scenario, sim)

        if results.get("npv"):
            npv_rows.append((*meta, *[results["npv"].get(t) for t in technologies]))
            npv_np_rows.append((*meta, *[results["npv_no_policy"].get(t) for t in technologies]))

        if results.get("cac"):
            cac_rows.append((*meta, *[results["cac"].get(t) for t in non_smr]))

        if results.get("carbon_intensity"):
            for tech in technologies:
                ci_vals = results["carbon_intensity"].get(tech, [])
                ci_rows.append((time, scenario, sim, tech, *ci_vals))

        if results.get("tax_credits"):
            for tech in non_smr:
                tc = results["tax_credits"].get(tech, {})
                tc_rows.append((
                    time, scenario, sim, tech,
                    tc.get("45V", 0), tc.get("45Q", 0), tc.get("45Y", 0), tc.get("48E", 0),
                ))

        if (sim + 1) % 50 == 0:
            context.log.info(f"  [{scenario}/{time}] {sim + 1}/{n_sims} simulations complete")

    dfs: dict[str, pd.DataFrame] = {}

    if npv_rows:
        dfs["NPV"] = pd.DataFrame(
            npv_rows, columns=["time", "scenario", "simulation"] + tech_cols
        )
        dfs["NPV_no_policy"] = pd.DataFrame(
            npv_np_rows, columns=["time", "scenario", "simulation"] + tech_cols
        )
    if cac_rows:
        dfs["CAC"] = pd.DataFrame(
            cac_rows, columns=["time", "scenario", "simulation"] + non_smr_cols
        )
    if ci_rows:
        dfs["CI"] = pd.DataFrame(
            ci_rows, columns=["time", "scenario", "simulation", "technology"] + _CI_YEARS
        )
    if tc_rows:
        dfs["TaxCredits"] = pd.DataFrame(
            tc_rows,
            columns=["time", "scenario", "simulation", "technology", "45V", "45Q", "45Y", "48E"],
        )

    context.log.info(
        f"Partition {context.partition_key} done: "
        f"{len(npv_rows)} NPV rows, {len(cac_rows)} CAC rows, "
        f"{len(ci_rows)} CI rows, {len(tc_rows)} TaxCredit rows"
    )
    return dfs
