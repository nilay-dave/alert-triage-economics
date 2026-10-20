"""Render the frontier analysis as HTML and as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ate.frontier.compute import REPORT_AT
from ate.frontier.summary import StreamSummary


def to_dict(summary: StreamSummary) -> dict:
    """Serialize the analysis. This is the shape CI and the report both read."""
    return {
        "stream": {
            "alerts": summary.alerts,
            "true_positives": summary.true_positives,
            "tp_rate": round(summary.tp_rate, 6),
            "one_in": round(1 / summary.tp_rate) if summary.tp_rate else None,
            "rules_analysed": summary.rules_analysed,
            "rules_skipped_low_volume": list(summary.rules_skipped_low_volume),
            "free_volume": summary.free_volume,
            "free_volume_pct": round(summary.free_volume_pct, 2),
            "free_hours": round(summary.free_hours, 1),
            "minutes_per_alert": summary.minutes_per_alert,
            "untunable_rules": [f.rule for f in summary.untunable],
            "untunable_volume_pct": round(summary.untunable_volume_pct, 2),
            "unmeasured_rules": [f.rule for f in summary.unmeasured],
            "unmeasured_volume_pct": round(summary.unmeasured_volume_pct, 2),
            # Keys carry no dots, matching docs/metrics.json, so the same path
            # works in the report, the JSON and the published-number check.
            "blanket_cut_cost": {
                f"cut_{int(f * 100)}": round(summary.cost_of(f), 2) for f in REPORT_AT
            },
        },
        "rules": [
            {
                "rule": f.rule,
                "alerts": f.alerts,
                "true_positives": f.true_positives,
                "tunable": f.tunable,
                "verdict": f.verdict.value,
                "separation": round(f.separation, 4),
                "separation_ci": [round(f.separation_low, 4), round(f.separation_high, 4)],
                "volume_removed_at_first_loss": round(f.volume_removed_at_first_loss, 4),
                "first_loss_ci": [round(f.first_loss_low, 4), round(f.first_loss_high, 4)],
                "loss_at": {str(k): round(v, 4) for k, v in f.loss_at.items()},
                "curve": [
                    {
                        "volume_removed": round(p.volume_removed, 5),
                        "true_positives_lost": round(p.true_positives_lost, 5),
                        "threshold": round(p.threshold, 4),
                    }
                    for p in f.curve
                ],
            }
            for f in summary.frontiers
        ],
    }


def render_json(summary: StreamSummary, out_path: Path | str) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(to_dict(summary), indent=2) + "\n", encoding="utf-8")
    return out_path


def chart_description(summary: StreamSummary) -> str:
    """Alt text that carries the chart's information, not its appearance.

    A sighted reader gets the shape: which lines bow below the diagonal and
    which sit on it. A non visual reader gets nothing from "a line chart of
    true positives lost against volume removed", so the text carries the
    verdict counts and names the rules the chart singles out.
    """
    tunable = [f.rule for f in summary.frontiers if f.tunable]
    parts = [
        f"Frontier chart for {summary.rules_analysed} "
        f"{'rule' if summary.rules_analysed == 1 else 'rules'}. "
        f"{len(tunable)} {'bows' if len(tunable) == 1 else 'bow'} below the no information "
        f"diagonal, meaning volume can be removed faster than detections are lost."
    ]
    if summary.untunable:
        names = ", ".join(f.rule for f in summary.untunable)
        count = len(summary.untunable)
        parts.append(
            f"{count} {'tracks' if count == 1 else 'track'} the diagonal and "
            f"cannot be tuned: {names}."
        )
    if summary.unmeasured:
        detail = ", ".join(
            f"{f.rule} with {f.true_positives} detections" for f in summary.unmeasured
        )
        count = len(summary.unmeasured)
        parts.append(
            f"{count} {'has' if count == 1 else 'have'} too few detections to judge: {detail}."
        )
    parts.append(
        f"Removing half of every rule's volume would cost {summary.cost_of(0.5):.1f} "
        "percent of true positives."
    )
    return " ".join(parts)


def render_html(
    summary: StreamSummary,
    out_path: Path | str,
    template_dir: Path | None = None,
    chart_paths: dict[str, str] | None = None,
) -> Path:
    template_dir = template_dir or Path(__file__).parent / "templates"
    # autoescape is set unconditionally rather than through select_autoescape,
    # which decides by final file extension and would leave a template named
    # report.html.j2 unescaped. Rule names come from somebody else's SIEM.
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    payload = to_dict(summary)
    html = env.get_template("report.html.j2").render(
        charts=chart_paths or {},
        chart_alt=chart_description(summary),
        **payload,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
