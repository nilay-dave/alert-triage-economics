"""Roll per rule frontiers up into the numbers a SOC lead acts on.

Two questions matter at the stream level and they have different answers.

"How much volume could we remove without losing anything" is the optimistic
number and it is the one that gets quoted. It is computed per rule and summed,
because tuning is done per rule.

"Which rules cannot be tuned at all" is the uncomfortable one. A rule whose
signal carries no information about truth has no frontier, and every threshold
on it trades detections for volume at the same rate. Reporting those separately
is the whole point: a tuning programme that leaves them in the "to do" column is
a tuning programme that will eventually delete detections and call it a win.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ate.config import Config
from ate.frontier.compute import REPORT_AT, RuleFrontier, Verdict, rule_frontier
from ate.logging import get_logger

log = get_logger(__name__)


@dataclass
class StreamSummary:
    alerts: int
    true_positives: int
    rules_analysed: int
    rules_skipped_low_volume: tuple[str, ...]
    frontiers: list[RuleFrontier] = field(default_factory=list)
    minutes_per_alert: float = 8.0

    @property
    def tp_rate(self) -> float:
        return self.true_positives / self.alerts if self.alerts else 0.0

    @property
    def untunable(self) -> list[RuleFrontier]:
        """Rules the evidence says should not be tuned."""
        return [f for f in self.frontiers if f.verdict is Verdict.NOT_TUNABLE]

    @property
    def unmeasured(self) -> list[RuleFrontier]:
        """Rules with too few detections for any verdict.

        Reported separately from untunable because the action differs: an
        untunable rule needs a better signal, an unmeasured one needs a longer
        window.
        """
        return [f for f in self.frontiers if f.verdict is Verdict.INSUFFICIENT_EVIDENCE]

    @property
    def free_volume(self) -> int:
        """Alerts removable across all rules without losing a true positive."""
        return int(sum(f.volume_removed_at_first_loss * f.alerts for f in self.frontiers))

    @property
    def free_volume_pct(self) -> float:
        return 100.0 * self.free_volume / self.alerts if self.alerts else 0.0

    @property
    def free_hours(self) -> float:
        """Analyst hours that volume represents, at the configured rate."""
        return self.free_volume * self.minutes_per_alert / 60.0

    @property
    def untunable_volume_pct(self) -> float:
        """Share of the stream produced by rules that cannot be tuned safely."""
        if not self.alerts:
            return 0.0
        return 100.0 * sum(f.alerts for f in self.untunable) / self.alerts

    @property
    def unmeasured_volume_pct(self) -> float:
        """Share of the stream produced by rules with too few detections."""
        if not self.alerts:
            return 0.0
        return 100.0 * sum(f.alerts for f in self.unmeasured) / self.alerts

    def cost_of(self, fraction: float) -> float:
        """True positives lost, as a percentage, if `fraction` of every rule's
        volume were removed. This is the number behind a blanket claim such as
        'we cut alert volume in half'."""
        total_tp = sum(f.true_positives for f in self.frontiers)
        if not total_tp:
            return 0.0
        lost = sum(f.loss_at.get(fraction, 0.0) * f.true_positives for f in self.frontiers)
        return 100.0 * lost / total_tp


def analyse(frame: pd.DataFrame, config: Config) -> StreamSummary:
    """Compute a frontier for every rule with enough volume to be worth tuning."""
    required = {"rule", "signal", "is_true_positive"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"alert corpus is missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("alert corpus is empty")

    counts = frame["rule"].value_counts()
    analysed, skipped = [], []
    for rule, count in counts.items():
        if count < config.min_rule_volume:
            skipped.append(str(rule))
            continue
        analysed.append(rule_frontier(frame, rule, config))

    analysed.sort(key=lambda f: -f.alerts)
    summary = StreamSummary(
        alerts=int(len(frame)),
        true_positives=int(frame["is_true_positive"].sum()),
        rules_analysed=len(analysed),
        rules_skipped_low_volume=tuple(sorted(skipped)),
        frontiers=analysed,
        minutes_per_alert=config.minutes_per_alert,
    )
    log.info(
        "frontier analysis complete",
        extra={
            "alerts": summary.alerts,
            "true_positives": summary.true_positives,
            "rules_analysed": summary.rules_analysed,
            "free_volume_pct": round(summary.free_volume_pct, 2),
            "untunable_rules": len(summary.untunable),
            "unmeasured_rules": len(summary.unmeasured),
            "cost_of_half": round(summary.cost_of(0.5), 2),
        },
    )
    return summary


__all__ = ["StreamSummary", "Verdict", "analyse", "REPORT_AT"]
