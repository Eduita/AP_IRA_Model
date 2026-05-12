"""YAML-driven simulation runner.

Usage::

    runner = SimulationRunner.from_config(Path("models/ap_ira.yaml"))
    runner.run()
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from ap_ira_lib.io.excel import dataframes_to_excel, get_current_est_time
from ap_ira_lib.pipeline.base import Pipeline, SimContext, Stage


def _load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _resolve_paths(config: dict, project_root: Path) -> dict:
    """Make all relative paths in the config absolute from the project root."""
    data_cfg = config.get("data", {})
    for key in data_cfg:
        data_cfg[key] = str(project_root / data_cfg[key])

    output_cfg = config.get("outputs", {})
    if "directory" in output_cfg:
        output_cfg["directory"] = str(project_root / output_cfg["directory"])

    for stage_cfg in config.get("pipeline", []):
        stage_config = stage_cfg.get("config", {})
        for key in ("parameters_file", "optimization_file", "ppa_file", "aeo_file"):
            if key in stage_config:
                stage_config[key] = str(project_root / stage_config[key])

    return config


def _build_stage(stage_cfg: dict) -> Stage:
    module_path = stage_cfg["module"]
    class_name = stage_cfg["class"]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(config=stage_cfg.get("config", {}))


def _build_pipeline(config: dict) -> Pipeline:
    stages = [_build_stage(s) for s in config["pipeline"]]
    return Pipeline(stages)


class SimulationRunner:
    def __init__(self, config: dict, project_root: Path):
        self.config = config
        self.project_root = project_root
        self.scenarios: list[str] = config["scenarios"]
        self.technologies: list[str] = config["technologies"]
        self.time_horizons: list[int] = config["time_horizons"]
        self.n_simulations: int = config["simulation"]["n_simulations"]
        self.matching: str = config["simulation"]["matching"]
        self.is_cbam: bool = config["simulation"].get("cbam", False)
        self.L: int = config["simulation"].get("L", 480)
        self.outputs_dir = Path(config["outputs"]["directory"])
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Start months indexed to time horizons (months from t0 = 2023)
        self.start_months: dict[int, int] = {
            t: (t - self.time_horizons[0]) * 12 for t in self.time_horizons
        }

        self._pipeline = _build_pipeline(config)
        self._aeo22_data, self._aeo23_data = self._load_aeo_data()

    @classmethod
    def from_config(cls, config_path: Path) -> "SimulationRunner":
        project_root = config_path.parent.parent
        config = _load_config(config_path)
        config = _resolve_paths(config, project_root)
        return cls(config, project_root)

    def _load_aeo_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        aeo_path = self.config["data"]["aeo_energy_mix"]
        aeo22 = pd.read_excel(aeo_path, sheet_name="AEO22", index_col=0)
        aeo23 = pd.read_excel(aeo_path, sheet_name="AEO23", index_col=0)
        return aeo22, aeo23

    def run(self) -> dict[str, pd.DataFrame]:
        """Run the full Monte Carlo simulation and return collected DataFrames."""
        print(f"[{get_current_est_time()}] Starting simulation: "
              f"{self.n_simulations} sims × {len(self.scenarios)} scenarios × {len(self.time_horizons)} time horizons")

        # Output collectors
        npv_rows, npv_np_rows, cac_rows, ci_rows, tc_rows = [], [], [], [], []
        ci_years = [str(2023 + i) for i in range(28)]

        for time in self.time_horizons:
            start_month = self.start_months[time]
            for scenario in self.scenarios:
                for sim in range(self.n_simulations):
                    np.random.seed(sim)

                    ctx = SimContext(
                        scenario=scenario,
                        start_month=start_month,
                        time=time,
                        sim_index=sim,
                        matching=self.matching,
                        technologies=self.technologies,
                        L=self.L,
                        policy=True,
                        is_cbam=self.is_cbam,
                        data={
                            "aeo22_data": self._aeo22_data,
                            "aeo23_data": self._aeo23_data,
                        },
                    )

                    ctx = self._pipeline.run(ctx)
                    results = ctx.data.get("dcf_results", {})

                    meta = (time, scenario, sim)

                    if results.get("npv"):
                        npv_rows.append((*meta, *[results["npv"].get(t) for t in self.technologies]))
                        npv_np_rows.append((*meta, *[results["npv_no_policy"].get(t) for t in self.technologies]))

                    if results.get("cac"):
                        cac_rows.append((*meta, *[results["cac"].get(t) for t in self.technologies if t != "AP SMR"]))

                    if results.get("carbon_intensity"):
                        for tech in self.technologies:
                            ci_vals = results["carbon_intensity"].get(tech, [])
                            ci_rows.append((time, scenario, sim, tech, *ci_vals))

                    if results.get("tax_credits"):
                        for tech in [t for t in self.technologies if t != "AP SMR"]:
                            tc = results["tax_credits"].get(tech, {})
                            tc_rows.append((time, scenario, sim, tech, tc.get("45V", 0), tc.get("45Q", 0),
                                            tc.get("45Y", 0), tc.get("48E", 0)))

                    msg = f"\r  [{time}] {scenario} sim {sim+1}/{self.n_simulations}"
                    sys.stdout.write(msg)
                    sys.stdout.flush()

                print()

        tech_cols = [t.replace(" ", "_") for t in self.technologies]
        non_smr = [t for t in self.technologies if t != "AP SMR"]
        non_smr_cols = [t.replace(" ", "_") for t in non_smr]

        dfs: dict[str, pd.DataFrame] = {}

        if npv_rows:
            dfs["NPV"] = pd.DataFrame(npv_rows, columns=["time", "scenario", "simulation"] + tech_cols)
            dfs["NPV_no_policy"] = pd.DataFrame(npv_np_rows, columns=["time", "scenario", "simulation"] + tech_cols)

        if cac_rows:
            dfs["CAC"] = pd.DataFrame(cac_rows, columns=["time", "scenario", "simulation"] + non_smr_cols)

        if ci_rows:
            dfs["CI"] = pd.DataFrame(ci_rows, columns=["time", "scenario", "simulation", "technology"] + ci_years)

        if tc_rows:
            dfs["TaxCredits"] = pd.DataFrame(
                tc_rows, columns=["time", "scenario", "simulation", "technology", "45V", "45Q", "45Y", "48E"]
            )

        timestamp = get_current_est_time().replace(":", "-").replace(" ", "_")
        output_path = self.outputs_dir / f"{timestamp}_results.xlsx"
        dataframes_to_excel(dfs, output_path)
        print(f"\n[{get_current_est_time()}] Done. Results written to {output_path}")

        return dfs
