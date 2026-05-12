"""Geometric Brownian Motion price path generator."""

import numpy as np


class BrownianMotion:
    def __init__(
        self,
        drift: float = 0.0,
        std_dev: float = 1.0,
        correlation: float = 0.0,
        n_steps: int = 100,
        seed: int | None = None,
    ):
        self.drift = drift
        self.std_dev = std_dev
        self.correlation = correlation
        self.n_steps = n_steps
        self.seed = seed

    def correlated_GBM(self, initial_prices: list[float]) -> tuple[np.ndarray, np.ndarray]:
        np.random.seed(self.seed)
        mean = [self.drift, self.drift]
        covariance = [
            [self.std_dev**2, self.std_dev**2 * self.correlation],
            [self.std_dev**2 * self.correlation, self.std_dev**2],
        ]
        samples = np.random.multivariate_normal(mean, covariance, self.n_steps)
        prices1 = initial_prices[0] * np.cumprod(np.exp(samples[:, 0]))
        prices2 = initial_prices[1] * np.cumprod(np.exp(samples[:, 1]))
        return prices1, prices2

    def uncorrelated_GBM(self, initial_price: float) -> np.ndarray:
        np.random.seed(self.seed)
        samples = np.random.normal(self.drift, self.std_dev, self.n_steps)
        return initial_price * np.cumprod(np.exp(samples))
