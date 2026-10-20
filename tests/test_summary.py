import numpy as np
import pandas as pd
import pytest

from ate.frontier.summary import analyse


def _stream(seed=7, alerts_per_rule=3_000):
    """Three rules: strongly separable, weakly separable, and pure noise."""
    rng = np.random.default_rng(seed)
    frames = []
    for rule, shift, true_positives in (("strong", 2.0, 60), ("weak", 0.8, 60), ("noise", 0.0, 20)):
        is_tp = np.zeros(alerts_per_rule, dtype=bool)
        is_tp[:true_positives] = True
        signal = rng.standard_normal(alerts_per_rule) + np.where(is_tp, shift, 0.0)
        frames.append(pd.DataFrame({"rule": rule, "signal": signal, "is_true_positive": is_tp}))
    return pd.concat(frames, ignore_index=True)


def test_missing_columns_are_rejected(config):
    with pytest.raises(ValueError, match="missing columns"):
        analyse(pd.DataFrame({"rule": ["a"], "signal": [1.0]}), config)


def test_empty_corpus_is_rejected(config):
    frame = pd.DataFrame({"rule": [], "signal": [], "is_true_positive": []})
    with pytest.raises(ValueError, match="empty"):
        analyse(frame, config)


def test_every_rule_with_enough_volume_is_analysed(config):
    summary = analyse(_stream(), config)
    assert summary.rules_analysed == 3
    assert summary.rules_skipped_low_volume == ()


def test_low_volume_rules_are_skipped_not_analysed(config):
    frame = pd.concat(
        [_stream(), pd.DataFrame({"rule": "tiny", "signal": [0.1, 0.2], "is_true_positive": [False, True]})],
        ignore_index=True,
    )
    summary = analyse(frame, config)
    assert "tiny" in summary.rules_skipped_low_volume
    assert summary.rules_analysed == 3


def test_noise_rule_is_reported_as_untunable(config):
    summary = analyse(_stream(), config)
    assert [f.rule for f in summary.untunable] == ["noise"]
    assert summary.untunable_volume_pct > 30


def test_free_volume_is_bounded_by_the_stream(config):
    summary = analyse(_stream(), config)
    assert 0 <= summary.free_volume <= summary.alerts
    assert 0.0 <= summary.free_volume_pct <= 100.0


def test_free_hours_follows_minutes_per_alert(config):
    from dataclasses import replace

    base = analyse(_stream(), config)
    doubled = analyse(_stream(), replace(config, minutes_per_alert=config.minutes_per_alert * 2))
    assert doubled.free_hours == pytest.approx(base.free_hours * 2, rel=0.01)


def test_cost_of_a_blanket_cut_rises_with_the_cut(config):
    """The number that refutes an uncosted tuning claim. It has to be monotonic
    or the tool is saying something incoherent."""
    summary = analyse(_stream(), config)
    costs = [summary.cost_of(f) for f in (0.1, 0.25, 0.5, 0.75, 0.9)]
    assert costs == sorted(costs)
    assert costs[-1] > costs[0]
    assert all(0.0 <= c <= 100.0 for c in costs)


def test_cost_of_an_unreported_fraction_is_zero(config):
    assert analyse(_stream(), config).cost_of(0.333) == 0.0


def test_tp_rate_matches_the_corpus(config):
    frame = _stream()
    summary = analyse(frame, config)
    assert summary.tp_rate == pytest.approx(frame["is_true_positive"].mean())


def test_frontiers_are_ordered_by_volume(config):
    summary = analyse(_stream(), config)
    volumes = [f.alerts for f in summary.frontiers]
    assert volumes == sorted(volumes, reverse=True)


def test_summary_with_no_true_positives_anywhere(config):
    frame = pd.DataFrame(
        {"rule": "r", "signal": np.linspace(0, 1, 500), "is_true_positive": False}
    )
    summary = analyse(frame, config)
    assert summary.true_positives == 0
    assert summary.free_volume == 0
    assert summary.cost_of(0.5) == 0.0
    assert summary.untunable == summary.frontiers
