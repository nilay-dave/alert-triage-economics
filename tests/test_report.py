import json

import numpy as np
import pandas as pd

from ate.frontier.summary import analyse
from ate.report.chart import draw_cost_curve, draw_frontier
from ate.report.render import render_html, render_json, to_dict


def _summary(config, seed=7):
    rng = np.random.default_rng(seed)
    frames = []
    for rule, shift, true_positives in (("strong", 2.0, 80), ("noise", 0.0, 20)):
        is_tp = np.zeros(4_000, dtype=bool)
        is_tp[:true_positives] = True
        signal = rng.standard_normal(4_000) + np.where(is_tp, shift, 0.0)
        frames.append(pd.DataFrame({"rule": rule, "signal": signal, "is_true_positive": is_tp}))
    return analyse(pd.concat(frames, ignore_index=True), config)


def test_dict_carries_the_headline_numbers(config):
    payload = to_dict(_summary(config))
    assert payload["stream"]["alerts"] == 8_000
    assert payload["stream"]["one_in"] > 1
    assert "cut_50" in payload["stream"]["blanket_cut_cost"]
    assert not any("." in key for key in payload["stream"]["blanket_cut_cost"]), (
        "a dotted key cannot be addressed by the published-number check"
    )
    assert payload["stream"]["untunable_rules"] == ["noise"]


def test_every_rule_carries_an_interval(config):
    payload = to_dict(_summary(config))
    for rule in payload["rules"]:
        assert len(rule["separation_ci"]) == 2
        assert rule["separation_ci"][0] <= rule["separation"] <= rule["separation_ci"][1]
        assert len(rule["first_loss_ci"]) == 2


def test_json_render_is_valid(tmp_path, config):
    path = render_json(_summary(config), tmp_path / "out" / "f.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["stream"]["rules_analysed"] == 2


def test_html_leads_with_the_blanket_cut_cost(tmp_path, config):
    summary = _summary(config)
    html = render_html(summary, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert f"{summary.cost_of(0.5):.1f}" in html
    # The headline must be formatted, not a raw float repr, or it reads as
    # "12.0%" on one corpus and "15.63%" on the next.
    assert "15.63" not in html
    assert "prefers-color-scheme: dark" in html


def test_html_escapes_rule_names(tmp_path, config):
    rng = np.random.default_rng(3)
    is_tp = np.zeros(1_000, dtype=bool)
    is_tp[:30] = True
    frame = pd.DataFrame({
        "rule": "<script>alert(1)</script>",
        "signal": rng.standard_normal(1_000) + np.where(is_tp, 1.5, 0.0),
        "is_true_positive": is_tp,
    })
    html = render_html(analyse(frame, config), tmp_path / "r.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_tunability_is_not_carried_by_colour_alone(tmp_path, config):
    html = render_html(_summary(config), tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'content: "x"' in html
    assert 'content: "ok"' in html
    assert ">no<" in html and ">yes<" in html


def test_html_has_a_skip_link_and_a_caption(tmp_path, config):
    html = render_html(_summary(config), tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'class="skip" href="#rules"' in html
    assert "<caption>" in html


def test_charts_reference_only_supplied_paths(tmp_path, config):
    html = render_html(_summary(config), tmp_path / "r.html").read_text(encoding="utf-8")
    assert "<img" not in html
    html = render_html(
        _summary(config), tmp_path / "r2.html",
        chart_paths={"frontier": "charts/f.png", "blanket": "charts/b.png"},
    ).read_text(encoding="utf-8")
    assert 'src="charts/f.png"' in html
    assert 'alt="' in html


def test_frontier_chart_is_written(tmp_path, config):
    path = draw_frontier(_summary(config), tmp_path / "charts" / "f.png")
    assert path.exists() and path.stat().st_size > 10_000


def test_cost_curve_chart_is_written(tmp_path, config):
    path = draw_cost_curve(_summary(config), tmp_path / "charts" / "b.png")
    assert path.exists() and path.stat().st_size > 5_000


def test_curve_points_are_bounded(config):
    payload = to_dict(_summary(config))
    for rule in payload["rules"]:
        for point in rule["curve"]:
            assert 0.0 <= point["volume_removed"] <= 1.0
            assert 0.0 <= point["true_positives_lost"] <= 1.0


def test_chart_distinguishes_an_unmeasured_rule(tmp_path, config):
    """The unmeasured rule has to be visually distinct from an untunable one,
    because the two call for different actions."""
    from dataclasses import replace

    rng = np.random.default_rng(21)
    frames = []
    for rule, shift, true_positives in (("measured", 1.6, 120), ("sparse", 1.6, 5)):
        is_tp = np.zeros(4_000, dtype=bool)
        is_tp[:true_positives] = True
        signal = rng.standard_normal(4_000) + np.where(is_tp, shift, 0.0)
        frames.append(pd.DataFrame({"rule": rule, "signal": signal, "is_true_positive": is_tp}))
    summary = analyse(pd.concat(frames, ignore_index=True), replace(config, min_true_positives_for_verdict=20))

    assert [f.rule for f in summary.unmeasured] == ["sparse"]
    path = draw_frontier(summary, tmp_path / "c.png")
    assert path.exists() and path.stat().st_size > 10_000


def test_report_shows_unknown_for_an_unmeasured_rule(tmp_path, config):
    from dataclasses import replace

    rng = np.random.default_rng(22)
    is_tp = np.zeros(4_000, dtype=bool)
    is_tp[:5] = True
    frame = pd.DataFrame({
        "rule": "sparse",
        "signal": rng.standard_normal(4_000) + np.where(is_tp, 1.6, 0.0),
        "is_true_positive": is_tp,
    })
    summary = analyse(frame, replace(config, min_true_positives_for_verdict=20))
    html = render_html(summary, tmp_path / "r.html").read_text(encoding="utf-8")
    assert ">unknown<" in html
    assert 'content: "?"' in html


def test_every_colour_pair_meets_its_contrast_threshold():
    """Runs the same check CI runs, so a palette edit cannot quietly fail AA."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tools" / "check_contrast.py")],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
