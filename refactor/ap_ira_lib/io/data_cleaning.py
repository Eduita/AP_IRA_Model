"""Optimization data loader and query helpers."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd


def load_optimization_data(file_path: Path | str) -> pd.DataFrame:
    """Load and clean the optimization results Excel file."""
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df = _convert_string_lists(df)
    df = df[~df["town"].isin(["Pryor"])]
    return df


def _convert_string_lists(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        for idx, val in df[col].items():
            if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
                try:
                    df.at[idx, col] = ast.literal_eval(val)
                except Exception:
                    pass
    return df


def get_generation_data(
    data: pd.DataFrame, year: int, matching: str, technology: str
) -> tuple[pd.Series | None, pd.Series | None]:
    """Return the min-cost and max-cost rows for a given year/matching/technology group."""
    grouped = data.groupby(["year", "matching", "technology"])
    try:
        group = grouped.get_group((year, matching, technology))
        return group.loc[group["cost"].idxmin()], group.loc[group["cost"].idxmax()]
    except KeyError:
        return None, None


def return_masked_random_row(
    data: pd.DataFrame, time: int, matching: str, tech: str, randomizer: float
) -> pd.Series:
    mask = (data["year"] == time) & (data["matching"] == matching) & (data["technology"] == tech)
    subset = data[mask]
    return subset.iloc[int(randomizer * len(subset))]


def get_closest_quantile_data(
    data: pd.DataFrame, year: int, matching: str, technology: str
) -> tuple[pd.Series | None, pd.Series | None, pd.Series | None]:
    """Return rows closest to Q1, Q3, and median cost for a given group."""
    grouped = data.groupby(["year", "matching", "technology"])
    try:
        group = grouped.get_group((year, matching, technology))
        q1 = group["cost"].quantile(0.25)
        median = group["cost"].median()
        q3 = group["cost"].quantile(0.75)
        return (
            group.loc[(group["cost"] - q1).abs().idxmin()],
            group.loc[(group["cost"] - q3).abs().idxmin()],
            group.loc[(group["cost"] - median).abs().idxmin()],
        )
    except KeyError:
        return None, None, None
