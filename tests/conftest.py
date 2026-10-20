"""Shared fixtures. No network, no services, no API keys."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from ate.config import Config

# Fast enough for a test run, wide enough that percentile intervals mean
# something. Tests that need a tight interval set it themselves.
TEST_RESAMPLES = 200


@pytest.fixture
def config() -> Config:
    return Config(
        minutes_per_alert=8.0,
        bootstrap_resamples=TEST_RESAMPLES,
        confidence=0.95,
        seed=7,
        min_rule_volume=50,
        bootstrap_noise_cap=5_000,
    )


def make_alerts(
    rule: str = "r",
    alerts: int = 2_000,
    true_positives: int = 40,
    shift: float = 1.5,
    seed: int = 7,
) -> pd.DataFrame:
    """Build one rule's alerts with a known separation.

    `shift` is how many standard deviations higher the signal runs on true
    positives. shift of 0.0 produces a rule with no usable frontier.
    """
    rng = np.random.default_rng(seed)
    is_tp = np.zeros(alerts, dtype=bool)
    is_tp[:true_positives] = True
    signal = rng.standard_normal(alerts) + np.where(is_tp, shift, 0.0)
    frame = pd.DataFrame({"rule": rule, "signal": signal, "is_true_positive": is_tp})
    return frame.sample(frac=1.0, random_state=seed).reset_index(drop=True)


@pytest.fixture
def alerts_factory():
    return make_alerts


@pytest.fixture
def fast_config(config):
    """Fewer resamples still, for tests that only check plumbing."""
    return replace(config, bootstrap_resamples=100, bootstrap_noise_cap=1_000)
