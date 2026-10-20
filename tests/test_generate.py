import numpy as np
import pandas as pd
import pytest

from ate.corpus.generate import generate
from ate.corpus.spec import load_spec


def test_zero_or_negative_alert_count_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="must be positive"):
        generate(tmp_path / "c.parquet", 0)


def test_requested_count_is_written(tmp_path):
    result = generate(tmp_path / "c.parquet", 20_000, seed=3)
    assert result.alerts == 20_000
    assert len(pd.read_parquet(result.path)) == 20_000
    assert sum(n for n, _ in result.per_rule.values()) == 20_000


def test_generation_is_deterministic_for_a_seed(tmp_path):
    a = pd.read_parquet(generate(tmp_path / "a.parquet", 20_000, seed=11).path)
    b = pd.read_parquet(generate(tmp_path / "b.parquet", 20_000, seed=11).path)
    assert a.equals(b)


def test_different_seeds_differ(tmp_path):
    a = pd.read_parquet(generate(tmp_path / "a.parquet", 20_000, seed=11).path)
    b = pd.read_parquet(generate(tmp_path / "b.parquet", 20_000, seed=12).path)
    assert not a.equals(b)


def test_corpus_has_the_three_required_columns(tmp_path):
    frame = pd.read_parquet(generate(tmp_path / "c.parquet", 5_000, seed=5).path)
    assert set(frame.columns) == {"rule", "signal", "is_true_positive"}
    assert frame["is_true_positive"].dtype == bool


def test_measured_imbalance_tracks_the_declared_one(tmp_path):
    """A generator that ignored tp_rate would still produce a plausible looking
    corpus, so this asserts the rate it actually produces."""
    spec = load_spec()
    result = generate(tmp_path / "c.parquet", 400_000, seed=9)
    assert abs(result.overall_tp_rate - spec.overall_tp_rate) < 0.0008


def test_per_rule_rates_track_the_declared_ones(tmp_path):
    spec = load_spec()
    result = generate(tmp_path / "c.parquet", 400_000, seed=9)
    for name, (count, true_positives) in result.per_rule.items():
        declared = spec.by_name(name).tp_rate
        measured = true_positives / count
        assert abs(measured - declared) < 0.004, f"{name}: {measured} against {declared}"


def test_rule_shares_track_the_declared_ones(tmp_path):
    spec = load_spec()
    result = generate(tmp_path / "c.parquet", 200_000, seed=4)
    for name, (count, _) in result.per_rule.items():
        assert abs(count / result.alerts - spec.by_name(name).share) < 0.01


def test_untunable_rule_signal_carries_no_information(tmp_path):
    """The rule declared with a zero shift must really have overlapping
    distributions, or the corpus does not contain the case it claims to."""
    spec = load_spec()
    untunable = next(r for r in spec.rules if not r.tunable)
    frame = pd.read_parquet(generate(tmp_path / "c.parquet", 400_000, seed=9).path)
    subset = frame[frame["rule"] == untunable.name]
    tp_mean = subset.loc[subset["is_true_positive"], "signal"].mean()
    noise_mean = subset.loc[~subset["is_true_positive"], "signal"].mean()
    assert abs(tp_mean - noise_mean) < 0.6


def test_tunable_rules_do_separate(tmp_path):
    spec = load_spec()
    frame = pd.read_parquet(generate(tmp_path / "c.parquet", 400_000, seed=9).path)
    for rule in spec.rules:
        if not rule.tunable or rule.signal_tp_shift < 1.0:
            continue
        subset = frame[frame["rule"] == rule.name]
        tp_mean = subset.loc[subset["is_true_positive"], "signal"].mean()
        noise_mean = subset.loc[~subset["is_true_positive"], "signal"].mean()
        assert tp_mean - noise_mean > 0.5, rule.name


def test_chunking_does_not_change_the_total(tmp_path):
    from ate.corpus import generate as module

    original = module.CHUNK_ROWS
    try:
        module.CHUNK_ROWS = 997
        result = generate(tmp_path / "c.parquet", 5_000, seed=2)
        assert result.alerts == 5_000
        assert len(pd.read_parquet(result.path)) == 5_000
    finally:
        module.CHUNK_ROWS = original


def test_every_declared_rule_appears(tmp_path):
    result = generate(tmp_path / "c.parquet", 100_000, seed=1)
    assert set(result.per_rule) == set(load_spec().names)
    assert all(count > 0 for count, _ in result.per_rule.values())


def test_signal_is_finite(tmp_path):
    frame = pd.read_parquet(generate(tmp_path / "c.parquet", 20_000, seed=6).path)
    assert np.isfinite(frame["signal"]).all()
