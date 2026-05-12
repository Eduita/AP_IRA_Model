"""Dagster resources for the AP IRA pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml
from dagster import ConfigurableResource


class ModelConfigResource(ConfigurableResource):
    """Loads and fully resolves the YAML model configuration.

    ``config_path`` is relative to the working directory where ``dagster dev``
    is launched (i.e. ``refactor/``).

    ``project_root`` is the root that all data paths in the YAML are anchored
    to.  Leave empty to auto-detect: the resource will walk three levels up
    from the YAML file — ``refactor/models/ap_ira.yaml`` → ``AP_IRA_Model/``.
    """

    config_path: str = "models/ap_ira.yaml"
    project_root: str = ""

    def load(self) -> dict:
        cfg_path = Path(self.config_path).resolve()

        if self.project_root:
            root = Path(self.project_root).resolve()
        else:
            # refactor/models/ap_ira.yaml → .parent = refactor/models/
            #   → .parent = refactor/ → .parent = AP_IRA_Model/
            root = cfg_path.parent.parent.parent

        with open(cfg_path) as f:
            config = yaml.safe_load(f)

        # Resolve all relative paths declared in the YAML to absolute paths.
        data_cfg = config.get("data", {})
        for key in list(data_cfg):
            data_cfg[key] = str(root / data_cfg[key])

        output_cfg = config.get("outputs", {})
        if "directory" in output_cfg:
            output_cfg["directory"] = str(root / output_cfg["directory"])

        for stage_cfg in config.get("pipeline", []):
            stage_config = stage_cfg.get("config", {})
            for key in ("parameters_file", "optimization_file", "ppa_file", "aeo_file"):
                if key in stage_config:
                    stage_config[key] = str(root / stage_config[key])

        return config
