import json

import numpy as np
import pandas as pd
from typer.testing import CliRunner

from ate import __version__
from ate.cli import app

runner = CliRunner()


def _corpus(tmp_path, seed=7, per_rule=3_000):
    rng = np.random.default_rng(seed)
    frames = []
    for rule, shift, true_positives in (("strong", 2.0, 60), ("noise", 0.0, 20)):
        is_tp = np.zeros(per_rule, dtype=bool)
        is_tp[:true_positives] = True
        signal = rng.standard_normal(per_rule) + np.where(is_tp, shift, 0.0)
        frames.append(pd.DataFrame({"rule": rule, "signal": signal, "is_true_positive": is_tp}))
    path = tmp_path / "alerts.parquet"
    pd.concat(frames, ignore_index=True).to_parquet(path, index=False)
    return path


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_generate_writes_a_corpus(tmp_path):
    out = tmp_path / "c.parquet"
    result = runner.invoke(app, ["generate", "--alerts", "5000", "--out", str(out), "--seed", "3"])
    assert result.exit_code == 0
    assert out.exists()
    assert "wrote 5,000 alerts" in result.output


def test_frontier_reports_the_blanket_cut_cost(tmp_path):
    result = runner.invoke(
        app, ["frontier", "--alerts", str(_corpus(tmp_path)), "--resamples", "100"]
    )
    assert result.exit_code == 0
    assert "cost of a blanket cut" in result.output
    assert "rules with no signal    1" in result.output


def test_frontier_writes_html_json_and_charts(tmp_path):
    html, js, charts = tmp_path / "r.html", tmp_path / "r.json", tmp_path / "charts"
    result = runner.invoke(app, [
        "frontier", "--alerts", str(_corpus(tmp_path)),
        "--out", str(html), "--json", str(js), "--charts", str(charts), "--resamples", "100",
    ])
    assert result.exit_code == 0
    assert "<!doctype html>" in html.read_text(encoding="utf-8")
    assert json.loads(js.read_text(encoding="utf-8"))["stream"]["rules_analysed"] == 2
    assert (charts / "frontier.png").exists()
    assert (charts / "blanket-cut.png").exists()


def test_frontier_rejects_a_missing_corpus(tmp_path):
    result = runner.invoke(app, ["frontier", "--alerts", str(tmp_path / "nope.parquet")])
    assert result.exit_code != 0


def test_gate_passes_within_the_loss_budget(tmp_path):
    result = runner.invoke(app, [
        "gate", "--alerts", str(_corpus(tmp_path)), "--cut", "0.1",
        "--max-tp-loss-pct", "90", "--resamples", "100",
    ])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_gate_fails_above_the_loss_budget(tmp_path):
    result = runner.invoke(app, [
        "gate", "--alerts", str(_corpus(tmp_path)), "--cut", "0.9",
        "--max-tp-loss-pct", "1", "--resamples", "100",
    ])
    assert result.exit_code == 2
    assert "FAIL" in result.output


def test_gate_rejects_a_cut_outside_zero_to_one(tmp_path):
    result = runner.invoke(app, [
        "gate", "--alerts", str(_corpus(tmp_path)), "--cut", "1.5", "--resamples", "100",
    ])
    assert result.exit_code != 0


def test_resamples_flag_overrides_the_default(tmp_path):
    result = runner.invoke(app, [
        "frontier", "--alerts", str(_corpus(tmp_path)), "--resamples", "120",
    ])
    assert result.exit_code == 0


def test_version_matches_package_metadata():
    from importlib.metadata import version

    assert __version__ == version("alert-triage-economics")


def test_frontier_reports_rules_with_too_few_detections(tmp_path):
    rng = np.random.default_rng(31)
    is_tp = np.zeros(6_000, dtype=bool)
    is_tp[:5] = True
    frame = pd.DataFrame({
        "rule": "sparse",
        "signal": rng.standard_normal(6_000) + np.where(is_tp, 1.6, 0.0),
        "is_true_positive": is_tp,
    })
    path = tmp_path / "sparse.parquet"
    frame.to_parquet(path, index=False)
    result = runner.invoke(app, ["frontier", "--alerts", str(path), "--resamples", "100"])
    assert result.exit_code == 0
    assert "too few detections      1" in result.output
    assert "sparse" in result.output


def test_gate_reports_both_verdict_counts(tmp_path):
    result = runner.invoke(app, [
        "gate", "--alerts", str(_corpus(tmp_path)), "--cut", "0.1",
        "--max-tp-loss-pct", "90", "--resamples", "100",
    ])
    assert "untunable rules" in result.output
    assert "unmeasured rules" in result.output


def test_charts_written_outside_the_report_directory_still_resolve(tmp_path):
    """The relative path from the report to the charts cannot be computed when
    the charts live outside the report's directory, so it falls back to the
    path as given."""
    html = tmp_path / "out" / "r.html"
    charts = tmp_path / "elsewhere" / "charts"
    result = runner.invoke(app, [
        "frontier", "--alerts", str(_corpus(tmp_path)),
        "--out", str(html), "--charts", str(charts), "--resamples", "100",
    ])
    assert result.exit_code == 0
    assert (charts / "frontier.png").exists()
    assert str(charts) in html.read_text(encoding="utf-8")


def test_every_declared_dependency_is_used():
    """An unused dependency is a claim the code does not support, and if it also
    sits in the README tech stack it is an advertised capability the project
    does not have. This caught scipy, which was declared and never imported."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tools" / "check_dependencies.py")],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
