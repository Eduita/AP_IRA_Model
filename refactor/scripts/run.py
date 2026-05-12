#!/usr/bin/env python
"""Entry point: run the AP IRA model from the project root.

    uv run python scripts/run.py
    uv run python scripts/run.py --config models/ap_ira.yaml
"""

import argparse
from pathlib import Path

from ap_ira_lib.pipeline.runner import SimulationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AP IRA financial model.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("models/ap_ira.yaml"),
        help="Path to the model YAML configuration file.",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    runner = SimulationRunner.from_config(config_path)
    runner.run()


if __name__ == "__main__":
    main()
