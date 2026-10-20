"""Configuration surface.

Every tunable the analysis depends on lives here, sourced from environment
variables with documented defaults. Nothing in the analysis path reads a literal
threshold, rate or capacity figure directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(ValueError):
    """Raised when configuration is present but unusable."""


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    """Runtime configuration for a frontier run."""

    # Minutes an analyst spends on one alert before dispositioning it. Used to
    # convert alert volume into hours, which is the unit a SOC manager budgets
    # in. 8 minutes is the default because it is a figure a reader can argue
    # with; it is not measured from anything and the README says so.
    minutes_per_alert: float = field(default_factory=lambda: _env_float("ATE_MINUTES_PER_ALERT", 8.0))

    # Bootstrap resamples used for the interval around a true positive count.
    bootstrap_resamples: int = field(default_factory=lambda: _env_int("ATE_BOOTSTRAP_RESAMPLES", 2000))

    # Two sided confidence level for every published interval.
    confidence: float = field(default_factory=lambda: _env_float("ATE_CONFIDENCE", 0.95))

    # Seed for every random path, so a run is reproducible.
    seed: int = field(default_factory=lambda: _env_int("ATE_SEED", 7))

    # A rule contributing fewer alerts than this is not worth tuning and is
    # excluded from the frontier to keep the chart readable.
    min_rule_volume: int = field(default_factory=lambda: _env_int("ATE_MIN_RULE_VOLUME", 50))

    # Detections a rule needs before a tunable verdict is allowed at all. Below
    # this the bootstrap cannot tell that the observed detections are
    # unrepresentative, because it resamples those same few over and over, and
    # it can produce a narrow interval around a badly wrong estimate. Measured
    # at 20: see ADR-005.
    min_true_positives_for_verdict: int = field(
        default_factory=lambda: _env_int("ATE_MIN_TRUE_POSITIVES", 20)
    )

    # Noise alerts drawn per bootstrap replicate. Both bootstrapped statistics
    # have sampling variance dominated by the true positive count, which is in
    # the tens to low hundreds, not by the noise count, which is in the tens of
    # thousands. Capping the noise pool makes a replicate roughly six times
    # cheaper and measurably does not change the interval. See ADR-002.
    bootstrap_noise_cap: int = field(default_factory=lambda: _env_int("ATE_BOOTSTRAP_NOISE_CAP", 20_000))

    def __post_init__(self) -> None:
        if self.minutes_per_alert <= 0:
            raise ConfigError(f"minutes_per_alert must be positive, got {self.minutes_per_alert}")
        if self.bootstrap_resamples < 100:
            raise ConfigError(f"bootstrap_resamples must be at least 100, got {self.bootstrap_resamples}")
        if not 0.5 < self.confidence < 1.0:
            raise ConfigError(f"confidence must be in (0.5, 1.0), got {self.confidence}")
        if self.min_rule_volume < 1:
            raise ConfigError(f"min_rule_volume must be at least 1, got {self.min_rule_volume}")
        if self.bootstrap_noise_cap < 100:
            raise ConfigError(f"bootstrap_noise_cap must be at least 100, got {self.bootstrap_noise_cap}")
        if self.min_true_positives_for_verdict < 1:
            raise ConfigError(
                f"min_true_positives_for_verdict must be at least 1, "
                f"got {self.min_true_positives_for_verdict}"
            )


def load_config() -> Config:
    """Build a Config from the environment."""
    return Config()
