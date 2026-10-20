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
    html = env.get_template("report.html.j2").render(charts=chart_paths or {}, **payload)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
