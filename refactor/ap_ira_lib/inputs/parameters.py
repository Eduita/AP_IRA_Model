"""Parameter loading and stochastic sampling from JSON configuration."""

import json
from pathlib import Path

import numpy as np


class ParameterSampler:
    """Samples or averages input parameters from a JSON file with distribution specs.

    Distribution specs in JSON:
      ["uniform", low, high]     → sampled from U(low, high)
      ["correlated", low, high]  → correlated uniform, tied to a single draw
      ["constant", val, ...]     → passed through as-is (list form)
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.constant_variables: dict = {}
        self.random_variables: dict = {}
        self._force_correlate = float(np.random.uniform(0, 1))

    def sample(self, parameters_file: Path | str) -> dict:
        """Load JSON and draw random samples. Returns the fully resolved parameter dict."""
        with open(parameters_file) as f:
            raw = json.load(f)
        return self._sample_recursive(raw)

    def average(self, parameters_file: Path | str) -> dict:
        """Load JSON and use midpoint values (deterministic mode)."""
        with open(parameters_file) as f:
            raw = json.load(f)
        return self._average_recursive(raw)

    def _sample_recursive(self, d: dict) -> dict:
        for key, value in d.items():
            if isinstance(value, dict):
                self._sample_recursive(value)
            elif isinstance(value, list):
                if value[0] == "uniform":
                    self.random_variables[key] = value[1:]
                    d[key] = float(np.random.uniform(*value[1:]))
                elif value[0] == "correlated":
                    self.random_variables[key] = value[1:]
                    d[key] = value[1] + (value[2] - value[1]) * self._force_correlate
                elif value[0] == "constant":
                    self.constant_variables[key] = value[1:]
                    d[key] = value[1:]
            else:
                self.constant_variables[key] = value
        return d

    def _average_recursive(self, d: dict) -> dict:
        for key, value in d.items():
            if isinstance(value, dict):
                self._average_recursive(value)
            elif isinstance(value, list):
                if value[0] == "uniform":
                    self.random_variables[key] = value[1:]
                    d[key] = float(np.mean(value[1:]))
                elif value[0] == "correlated":
                    self.random_variables[key] = value[1:]
                    d[key] = value[1] + (value[2] - value[1]) * 0.5
                elif value[0] == "constant":
                    self.constant_variables[key] = value[1:]
                    d[key] = value[1:]
            else:
                self.constant_variables[key] = value
        return d
