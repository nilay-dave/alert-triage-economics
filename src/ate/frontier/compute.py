"""Compute the tuning frontier for each rule.

The claim this module exists to replace is "we reduced false positives by 60
percent". That sentence is on a great many SOC resumes and it is almost never
costed, because costing it requires knowing how many real detections went with
the noise. This computes that, per rule, across every threshold the rule's
signal offers.

For a rule with N alerts, sorting by the tuning signal descending and keeping
the top k gives one candidate tuning per k. For each one, two numbers matter:

    volume removed      (N - k) / N
    true positives lost (TP_total - TP_in_top_k) / TP_total

Plotting one against the other is the frontier. A steep early rise means the
rule can be tuned hard before it costs anything. A diagonal means the signal
carries no information and tuning is just deleting detections at random.

The number a SOC lead actually wants is the first point where the frontier
starts costing: the volume removable before the first true positive is lost.
That is `volume_removed_at_first_loss` and it is the figure this repository
leads with.

Bootstrap intervals are not optional here. The corpus has rules with a dozen
true positives in half a million alerts. A point estimate computed from twelve
observations implies a precision that does not exist, and quoting one is the
same error as the claim this tool is built to replace.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ate.config import Config
from ate.logging import get_logger

log = get_logger(__name__)

# Fractions of volume removed at which the frontier is reported. The curve is
# computed at every threshold; these are the points tabulated and published.
REPORT_AT = (0.1, 0.25, 0.5, 0.75, 0.9)


@dataclass(frozen=True)
class FrontierPoint:
    volume_removed: float
    true_positives_lost: float
    threshold: float


@dataclass(frozen=True)
class RuleFrontier:
    rule: str
    alerts: int
    true_positives: int
    curve: tuple[FrontierPoint, ...]
    # Volume removable before the first true positive is lost.
    volume_removed_at_first_loss: float
    # True positives lost at each fraction in REPORT_AT.
    loss_at: dict[float, float]
    # Bootstrap interval on volume_removed_at_first_loss.
    first_loss_low: float
    first_loss_high: float
    # Area under the frontier. 0.5 is a rule whose signal carries no
    # information; 1.0 would be a signal that separates perfectly.
    separation: float
    separation_low: float
    separation_high: float

    @property
    def tunable(self) -> bool:
        """True when the signal carries information beyond chance.

        The interval, not the point estimate, decides. A separation of 0.58
        measured on twelve true positives is not evidence of a tunable rule.
        """
        return self.separation_low > 0.5

    @property
    def hours_saved_at_first_loss(self) -> float:
        """Placeholder filled by the caller, which knows minutes per alert."""
        return 0.0


def _curve(signal: np.ndarray, is_tp: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Volume removed, true positives lost, and threshold at every cut point.

    Alerts are sorted by signal descending, so index k means "keep the k
    highest scoring alerts and suppress the rest".
    """
    order = np.argsort(-signal, kind="stable")
    sorted_signal = signal[order]
    sorted_tp = is_tp[order].astype(np.int64)

    total = len(sorted_tp)
    total_tp = int(sorted_tp.sum())
    kept_tp = np.cumsum(sorted_tp)

    keep = np.arange(1, total + 1)
    volume_removed = (total - keep) / total
    if total_tp == 0:
        true_positives_lost = np.zeros(total)
    else:
        true_positives_lost = (total_tp - kept_tp) / total_tp
    return volume_removed, true_positives_lost, sorted_signal


def _separation(signal: np.ndarray, is_tp: np.ndarray) -> float:
    """Probability a random true positive scores above a random noise alert.

    This is the Mann Whitney U statistic normalised, which is the same quantity
    as the area under an ROC curve. 0.5 means the signal is noise. It is
    computed from ranks rather than by sampling pairs, so it is exact.
    """
    positives = signal[is_tp]
    negatives = signal[~is_tp]
    if len(positives) == 0 or len(negatives) == 0:
        return 0.5
    ranks = pd.Series(signal).rank().to_numpy()
    rank_sum = ranks[is_tp].sum()
    n_pos, n_neg = len(positives), len(negatives)
    u = rank_sum - n_pos * (n_pos + 1) / 2
    return float(u / (n_pos * n_neg))


def _first_loss(volume_removed: np.ndarray, true_positives_lost: np.ndarray) -> float:
    """The most volume removable while losing zero true positives.

    `true_positives_lost` is non increasing in k, so it reaches zero at the
    index of the last true positive in signal order and stays there. The first
    such index is the smallest k that still keeps every detection, which is the
    largest removable volume. Taking the last index instead returns k equal to
    the corpus size, which is always a removable volume of zero.
    """
    clean = np.flatnonzero(true_positives_lost <= 0.0)
    if clean.size == 0:
        return 0.0
    return float(volume_removed[clean[0]])


def _bootstrap(
    signal: np.ndarray,
    is_tp: np.ndarray,
    config: Config,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Percentile intervals for first loss volume and for separation.

    Resampling is stratified: true positives and noise alerts are resampled
    within their own groups so every replicate holds the same number of true
    positives as the original. An unstratified bootstrap on a rule with twelve
    true positives draws replicates with zero of them, where neither statistic
    is defined, and the resulting interval is an artefact of that rather than a
    statement about the rule.
    """
    rng = np.random.default_rng(config.seed)
    positive_index = np.flatnonzero(is_tp)
    negative_index = np.flatnonzero(~is_tp)

    if positive_index.size == 0 or negative_index.size == 0:
        return (0.0, 0.0), (0.5, 0.5)

    first_losses = np.empty(config.bootstrap_resamples)
    separations = np.empty(config.bootstrap_resamples)

    for replicate in range(config.bootstrap_resamples):
        sampled_pos = rng.choice(positive_index, size=positive_index.size, replace=True)
        sampled_neg = rng.choice(negative_index, size=negative_index.size, replace=True)
        index = np.concatenate([sampled_pos, sampled_neg])
        replicate_signal = signal[index]
        replicate_tp = np.concatenate(
            [np.ones(sampled_pos.size, dtype=bool), np.zeros(sampled_neg.size, dtype=bool)]
        )
        volume, lost, _ = _curve(replicate_signal, replicate_tp)
        first_losses[replicate] = _first_loss(volume, lost)
        separations[replicate] = _separation(replicate_signal, replicate_tp)

    tail = (1.0 - config.confidence) / 2.0
    low, high = 100 * tail, 100 * (1.0 - tail)
    return (
        (float(np.percentile(first_losses, low)), float(np.percentile(first_losses, high))),
        (float(np.percentile(separations, low)), float(np.percentile(separations, high))),
    )


def rule_frontier(frame: pd.DataFrame, rule: str, config: Config) -> RuleFrontier:
    """Compute the frontier for one rule."""
    subset = frame[frame["rule"] == rule]
    signal = subset["signal"].to_numpy(dtype=np.float64)
    is_tp = subset["is_true_positive"].to_numpy(dtype=bool)

    volume, lost, thresholds = _curve(signal, is_tp)
    separation = _separation(signal, is_tp)
    (first_low, first_high), (sep_low, sep_high) = _bootstrap(signal, is_tp, config)

    loss_at = {
        fraction: float(np.interp(fraction, volume[::-1], lost[::-1])) for fraction in REPORT_AT
    }

    # The published curve is thinned to at most 400 points so the JSON and the
    # chart stay small. Thinning is by index, so the shape is preserved.
    step = max(1, len(volume) // 400)
    curve = tuple(
        FrontierPoint(
            volume_removed=float(volume[i]),
            true_positives_lost=float(lost[i]),
            threshold=float(thresholds[i]),
        )
        for i in range(0, len(volume), step)
    )

    return RuleFrontier(
        rule=rule,
        alerts=int(len(subset)),
        true_positives=int(is_tp.sum()),
        curve=curve,
        volume_removed_at_first_loss=_first_loss(volume, lost),
        loss_at=loss_at,
        first_loss_low=first_low,
        first_loss_high=first_high,
        separation=separation,
        separation_low=sep_low,
        separation_high=sep_high,
    )
