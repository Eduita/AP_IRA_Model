"""Partition definitions for the AP IRA simulation pipeline."""

from dagster import StaticPartitionsDefinition

SCENARIOS: list[str] = ["A", "B", "C", "D"]
TIME_HORIZONS: list[int] = [2023, 2030]

scenario_horizon_partitions = StaticPartitionsDefinition(
    [f"{s}_{t}" for s in SCENARIOS for t in TIME_HORIZONS]
)


def parse_partition_key(key: str) -> tuple[str, int]:
    """Parse 'A_2023' → ('A', 2023)."""
    scenario, time = key.rsplit("_", 1)
    return scenario, int(time)
