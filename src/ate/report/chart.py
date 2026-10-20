"""Draw the frontier.

One chart carries this repository: volume removed on the x axis, true positives
lost on the y axis, one line per rule. A rule that hugs the bottom can be tuned
hard before it costs anything. A rule that tracks the diagonal is being tuned by
deleting detections at random, and the diagonal is drawn so that comparison is
immediate rather than inferred.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ate.frontier.summary import StreamSummary  # noqa: E402

# Colour never carries meaning on its own here: every line is also labelled, and
# untunable rules are dashed as well as grey.
TUNABLE_COLOURS = ["#1f4e79", "#2e7d5b", "#8a5a00", "#6a3d9a", "#a3251c", "#0f6f84", "#7a5c2e"]
UNTUNABLE_COLOUR = "#8c8c8c"
UNMEASURED_COLOUR = "#b07d2b"


def draw_frontier(summary: StreamSummary, out_path: Path | str, dpi: int = 160) -> Path:
    """Write the frontier chart as a PNG."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(figsize=(9.0, 5.6))
    axes.plot(
        [0, 1], [0, 1],
        color="#b0b0b0", linestyle=":", linewidth=1.2, zorder=1,
        label="no information (tuning at random)",
    )

    tunable_index = 0
    for frontier in summary.frontiers:
        x = [point.volume_removed for point in frontier.curve][::-1]
        y = [point.true_positives_lost for point in frontier.curve][::-1]
        from ate.frontier.compute import Verdict

        if frontier.verdict is Verdict.TUNABLE:
            colour = TUNABLE_COLOURS[tunable_index % len(TUNABLE_COLOURS)]
            tunable_index += 1
            style, width = "-", 1.8
            label = f"{frontier.rule} (sep {frontier.separation:.2f})"
        elif frontier.verdict is Verdict.NOT_TUNABLE:
            colour, style, width = UNTUNABLE_COLOUR, "--", 2.0
            label = f"{frontier.rule} (no usable signal)"
        else:
            colour, style, width = UNMEASURED_COLOUR, "-.", 2.0
            label = f"{frontier.rule} ({frontier.true_positives} detections, too few to judge)"
        axes.plot(x, y, color=colour, linestyle=style, linewidth=width, zorder=2, label=label)

    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_xlabel("Share of this rule's alert volume removed")
    axes.set_ylabel("Share of this rule's true positives lost")
    axes.set_title(
        f"Tuning frontier by rule\n"
        f"{summary.alerts:,} alerts, {summary.true_positives:,} true positives "
        f"(1 in {1 / summary.tp_rate:.0f}), simulated corpus",
        fontsize=11, loc="left",
    )
    axes.grid(True, linewidth=0.4, alpha=0.4)
    axes.set_axisbelow(True)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    axes.legend(fontsize=8, loc="upper left", frameon=False, ncol=1)

    figure.tight_layout()
    figure.savefig(out_path, dpi=dpi)
    plt.close(figure)
    return out_path


def draw_cost_curve(summary: StreamSummary, out_path: Path | str, dpi: int = 160) -> Path:
    """Write the blanket cut chart: what a flat percentage cut costs overall."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    from ate.frontier.compute import REPORT_AT

    fractions = list(REPORT_AT)
    costs = [summary.cost_of(f) for f in fractions]

    figure, axes = plt.subplots(figsize=(7.2, 4.4))
    bars = axes.bar(
        [f"{int(f * 100)}%" for f in fractions], costs,
        color="#a3251c", width=0.62, zorder=2,
    )
    for bar, cost in zip(bars, costs, strict=True):
        axes.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.0,
            f"{cost:.1f}%", ha="center", va="bottom", fontsize=9,
        )

    axes.set_xlabel("Alert volume removed from every rule")
    axes.set_ylabel("True positives lost")
    axes.set_title(
        "What a blanket volume cut actually costs\nsimulated corpus",
        fontsize=11, loc="left",
    )
    axes.set_ylim(0, max(costs + [10]) * 1.25)
    axes.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    axes.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    axes.set_axisbelow(True)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)

    figure.tight_layout()
    figure.savefig(out_path, dpi=dpi)
    plt.close(figure)
    return out_path
