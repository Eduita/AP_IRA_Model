"""AP IRA Dagster pipeline.

Entry point for ``dagster dev`` and the Dagster UI.

Quick start
-----------
From ``AP_IRA_Model/refactor/``:

    uv run dagster dev

Then open http://localhost:3000 and:
  1. Materialise all partitions of ``simulation_results`` (simulation_job).
  2. Materialise ``merged_results`` + ``excel_output`` (aggregation_job).
"""

from dagster import Definitions, load_assets_from_modules

from .assets import outputs, simulations
from .jobs import aggregation_job, simulation_job
from .resources import ModelConfigResource

_all_assets = load_assets_from_modules([simulations, outputs])

defs = Definitions(
    assets=_all_assets,
    resources={
        "model_config": ModelConfigResource(
            config_path="models/ap_ira.yaml",
            # project_root left empty → auto-detected as AP_IRA_Model/ (3 levels up from YAML)
        ),
    },
    jobs=[simulation_job, aggregation_job],
)
