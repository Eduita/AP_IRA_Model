"""Tests for BrownianMotion price path generator."""

import numpy as np
import pytest

from ap_ira_lib.core.gbm import BrownianMotion


# ── uncorrelated_gbm ──────────────────────────────────────────────────────────


def test_uncorrelated_gbm_shape():
    bm = BrownianMotion(n_steps=100, seed=0)
    prices = bm.uncorrelated_gbm(100.0)
    assert prices.shape == (100,)


def test_uncorrelated_gbm_all_positive():
    bm = BrownianMotion(drift=0.0, std_dev=0.2, n_steps=200, seed=42)
    prices = bm.uncorrelated_gbm(50.0)
    assert (prices > 0).all()


def test_uncorrelated_gbm_reproducible_with_same_seed():
    bm_a = BrownianMotion(drift=0.01, std_dev=0.15, n_steps=50, seed=7)
    bm_b = BrownianMotion(drift=0.01, std_dev=0.15, n_steps=50, seed=7)
    np.testing.assert_array_equal(bm_a.uncorrelated_gbm(100.0), bm_b.uncorrelated_gbm(100.0))


def test_uncorrelated_gbm_different_seeds_differ():
    bm_a = BrownianMotion(n_steps=30, seed=1)
    bm_b = BrownianMotion(n_steps=30, seed=2)
    assert not np.array_equal(bm_a.uncorrelated_gbm(1.0), bm_b.uncorrelated_gbm(1.0))


def test_uncorrelated_gbm_near_initial_when_zero_vol():
    bm = BrownianMotion(drift=0.0, std_dev=1e-6, n_steps=100, seed=0)
    prices = bm.uncorrelated_gbm(200.0)
    assert abs(prices[-1] - 200.0) < 1.0


# ── correlated_gbm ────────────────────────────────────────────────────────────


def test_correlated_gbm_shape():
    bm = BrownianMotion(n_steps=100, correlation=0.8, seed=0)
    p1, p2 = bm.correlated_gbm([100.0, 200.0])
    assert p1.shape == (100,)
    assert p2.shape == (100,)


def test_correlated_gbm_all_positive():
    bm = BrownianMotion(drift=0.0, std_dev=0.1, n_steps=50, seed=99)
    p1, p2 = bm.correlated_gbm([50.0, 80.0])
    assert (p1 > 0).all()
    assert (p2 > 0).all()


def test_correlated_gbm_reproducible():
    bm_a = BrownianMotion(std_dev=0.2, correlation=0.5, n_steps=40, seed=3)
    bm_b = BrownianMotion(std_dev=0.2, correlation=0.5, n_steps=40, seed=3)
    a1, a2 = bm_a.correlated_gbm([100.0, 200.0])
    b1, b2 = bm_b.correlated_gbm([100.0, 200.0])
    np.testing.assert_array_equal(a1, b1)
    np.testing.assert_array_equal(a2, b2)


@pytest.mark.parametrize("initial", [[10.0, 10.0], [100.0, 500.0], [1.0, 1.0]])
def test_correlated_gbm_initial_prices_respected(initial):
    bm = BrownianMotion(drift=0.0, std_dev=1e-6, n_steps=50, seed=0)
    p1, p2 = bm.correlated_gbm(initial)
    assert abs(p1[0] - initial[0]) < 0.1 * initial[0]
    assert abs(p2[0] - initial[1]) < 0.1 * initial[1]
