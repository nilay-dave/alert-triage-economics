"""The statistics. These are the tests that matter most in this repository,
because a wrong frontier is a confidently wrong recommendation."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from tests.conftest import make_alerts

from ate.frontier.compute import (
    _curve,
    _first_loss,
    _replicate_statistics,
    _separation,
    rule_frontier,
)


def test_curve_on_a_worked_example():
    """Ten alerts, true positives at sorted positions 4 and 8. Keeping the top
    8 keeps both, so 20 percent of volume is removable at zero loss."""
    signal = np.arange(10, 0, -1).astype(float)
    is_tp = np.array([0, 0, 0, 1, 0, 0, 0, 1, 0, 0], dtype=bool)
    volume, lost, _ = _curve(signal, is_tp)
    assert volume[0] == pytest.approx(0.9)
    assert volume[-1] == pytest.approx(0.0)
    assert lost[0] == pytest.approx(1.0)
    assert lost[-1] == pytest.approx(0.0)
    assert _first_loss(volume, lost, 2) == pytest.approx(0.2)


def test_first_loss_takes_the_largest_removable_volume():
    """Regression: taking the last zero loss index instead of the first returns
    the smallest removable volume, which is always zero."""
    signal = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    is_tp = np.array([1, 1, 0, 0, 0], dtype=bool)
    volume, lost, _ = _curve(signal, is_tp)
    assert _first_loss(volume, lost, 2) == pytest.approx(0.6)


def test_first_loss_is_zero_when_the_worst_alert_is_a_true_positive():
    signal = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    is_tp = np.array([0, 0, 0, 0, 1], dtype=bool)
    volume, lost, _ = _curve(signal, is_tp)
    assert _first_loss(volume, lost, 1) == pytest.approx(0.0)


def test_first_loss_with_no_true_positives_is_zero():
    """Regression: with no detections in the window every cut point is
    trivially lossless, and reading the curve literally reported that the whole
    rule could be suppressed for free. There is no evidence either way, so the
    answer is zero."""
    signal = np.array([3.0, 2.0, 1.0])
    is_tp = np.zeros(3, dtype=bool)
    volume, lost, _ = _curve(signal, is_tp)
    assert _first_loss(volume, lost, 0) == pytest.approx(0.0)


def test_separation_of_a_perfect_signal_is_one():
    signal = np.array([9.0, 8.0, 1.0, 0.0])
    is_tp = np.array([1, 1, 0, 0], dtype=bool)
    assert _separation(signal, is_tp) == pytest.approx(1.0)


def test_separation_of_an_inverted_signal_is_zero():
    signal = np.array([9.0, 8.0, 1.0, 0.0])
    is_tp = np.array([0, 0, 1, 1], dtype=bool)
    assert _separation(signal, is_tp) == pytest.approx(0.0)


def test_separation_of_pure_noise_is_near_a_half():
    frame = make_alerts(alerts=40_000, true_positives=400, shift=0.0, seed=3)
    value = _separation(frame["signal"].to_numpy(), frame["is_true_positive"].to_numpy())
    assert 0.45 < value < 0.55


def test_separation_with_one_class_absent_is_a_half():
    signal = np.array([1.0, 2.0, 3.0])
    assert _separation(signal, np.zeros(3, dtype=bool)) == pytest.approx(0.5)
    assert _separation(signal, np.ones(3, dtype=bool)) == pytest.approx(0.5)


def test_replicate_statistics_match_the_curve_based_path():
    """The fast path exists for speed only. If it ever disagrees with the curve
    it is wrong, because the curve is the definition."""
    for seed in (1, 2, 3):
        frame = make_alerts(alerts=4_000, true_positives=60, shift=1.2, seed=seed)
        signal = frame["signal"].to_numpy()
        is_tp = frame["is_true_positive"].to_numpy()
        volume, lost, _ = _curve(signal, is_tp)
        expected = (_first_loss(volume, lost, int(is_tp.sum())), _separation(signal, is_tp))
        assert _replicate_statistics(signal, is_tp) == pytest.approx(expected)


def test_frontier_on_a_separable_rule_is_tunable(config, alerts_factory):
    frame = alerts_factory(alerts=6_000, true_positives=120, shift=2.0, seed=4)
    result = rule_frontier(frame, "r", config)
    assert result.tunable
    assert result.separation > 0.85
    assert result.separation_low > 0.5
    assert result.volume_removed_at_first_loss > 0.0


def test_frontier_on_a_noise_rule_is_not_tunable(config, alerts_factory):
    """The case the tool exists to catch. A point estimate above 0.5 is not
    evidence; the interval has to clear chance."""
    frame = alerts_factory(alerts=6_000, true_positives=15, shift=0.0, seed=5)
    result = rule_frontier(frame, "r", config)
    assert not result.tunable
    assert result.separation_low <= 0.5


def test_a_high_first_loss_does_not_make_a_noise_rule_tunable(config, alerts_factory):
    """With very few true positives the lowest scoring one can land high by
    chance, which makes first loss volume look generous on a rule that carries
    no signal at all. The separation interval is what prevents acting on it."""
    frame = alerts_factory(alerts=20_000, true_positives=8, shift=0.0, seed=17)
    result = rule_frontier(frame, "r", config)
    assert not result.tunable


def test_interval_is_wider_when_there_are_fewer_true_positives(config, alerts_factory):
    many = rule_frontier(alerts_factory(alerts=20_000, true_positives=400, shift=1.0, seed=6), "r", config)
    few = rule_frontier(alerts_factory(alerts=20_000, true_positives=15, shift=1.0, seed=6), "r", config)
    assert (few.separation_high - few.separation_low) > (many.separation_high - many.separation_low)


def test_loss_at_is_monotonic(config, alerts_factory):
    result = rule_frontier(alerts_factory(alerts=6_000, true_positives=120, shift=1.2, seed=7), "r", config)
    values = [result.loss_at[f] for f in sorted(result.loss_at)]
    assert values == sorted(values)
    assert all(0.0 <= v <= 1.0 for v in values)


def test_curve_is_thinned_but_keeps_its_endpoints(config, alerts_factory):
    result = rule_frontier(alerts_factory(alerts=50_000, true_positives=200, shift=1.0, seed=8), "r", config)
    assert len(result.curve) <= 420
    assert result.curve[0].volume_removed > 0.99
    assert result.curve[-1].volume_removed < 0.01


def test_bootstrap_is_reproducible_for_a_seed(config, alerts_factory):
    frame = alerts_factory(alerts=5_000, true_positives=80, shift=1.0, seed=9)
    first = rule_frontier(frame, "r", config)
    second = rule_frontier(frame, "r", config)
    assert first.separation_low == second.separation_low
    assert first.first_loss_high == second.first_loss_high


def test_noise_cap_does_not_move_the_interval(config, alerts_factory):
    """ADR-002's claim, asserted. Capping the noise pool must change the
    interval by less than the bootstrap's own resampling noise."""
    frame = alerts_factory(alerts=30_000, true_positives=200, shift=1.3, seed=10)
    capped = rule_frontier(frame, "r", replace(config, bootstrap_noise_cap=3_000))
    full = rule_frontier(frame, "r", replace(config, bootstrap_noise_cap=1_000_000))
    capped_width = capped.separation_high - capped.separation_low
    full_width = full.separation_high - full.separation_low
    assert abs(capped_width - full_width) < 0.02
    assert abs(capped.separation_low - full.separation_low) < 0.02


def test_rule_with_no_true_positives_has_a_degenerate_interval(config):
    frame = pd.DataFrame(
        {"rule": "r", "signal": np.linspace(0, 1, 500), "is_true_positive": False}
    )
    result = rule_frontier(frame, "r", config)
    assert result.true_positives == 0
    assert result.separation == pytest.approx(0.5)
    assert not result.tunable


def test_verdict_is_insufficient_evidence_below_the_minimum(config, alerts_factory):
    from dataclasses import replace

    from ate.frontier.compute import Verdict

    frame = alerts_factory(alerts=10_000, true_positives=6, shift=2.0, seed=12)
    result = rule_frontier(frame, "r", replace(config, min_true_positives_for_verdict=20))
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert not result.tunable, "an unmeasured rule must never read as tunable"


def test_verdict_is_tunable_at_or_above_the_minimum(config, alerts_factory):
    from dataclasses import replace

    from ate.frontier.compute import Verdict

    frame = alerts_factory(alerts=10_000, true_positives=200, shift=2.0, seed=12)
    result = rule_frontier(frame, "r", replace(config, min_true_positives_for_verdict=20))
    assert result.verdict is Verdict.TUNABLE
    assert result.tunable


def test_verdict_is_not_tunable_for_a_measured_noise_rule(config, alerts_factory):
    from dataclasses import replace

    from ate.frontier.compute import Verdict

    frame = alerts_factory(alerts=20_000, true_positives=200, shift=0.0, seed=13)
    result = rule_frontier(frame, "r", replace(config, min_true_positives_for_verdict=20))
    assert result.verdict is Verdict.NOT_TUNABLE
    assert not result.tunable


def test_a_false_tunable_above_the_minimum_still_looks_marginal(config, alerts_factory):
    """What the detection minimum actually buys.

    It does not drive the false tunable rate to zero and nothing can: a 95
    percent interval is wrong about 5 percent of the time by construction. What
    it buys is that above the threshold a false positive arrives with a lower
    bound sitting close to 0.5, so a reader sees weak evidence as weak. Below
    the threshold the interval is narrow around a wrong estimate and carries no
    warning at all.

    This replaced a test asserting no seed came back tunable, which was pinning
    an overclaim in ADR-005 rather than a property of the tool.
    """
    from dataclasses import replace

    fast = replace(config, bootstrap_resamples=150, bootstrap_noise_cap=2_000)
    false_positives = 0
    for seed in range(25):
        frame = alerts_factory(alerts=4_000, true_positives=40, shift=0.0, seed=300 + seed)
        result = rule_frontier(frame, "r", fast)
        if result.tunable:
            false_positives += 1
            assert result.separation_low < 0.58, (
                f"seed {seed}: a no signal rule read tunable with a lower bound of "
                f"{result.separation_low:.3f}, which is not marginal"
            )

    # Roughly the nominal rate. A much higher rate would mean the interval is
    # not covering; zero across 25 draws would be surprising rather than good.
    assert false_positives <= 5, f"{false_positives} of 25 is above the nominal rate"


def test_first_loss_with_an_all_lossy_curve_is_zero():
    """Defensive path: if no cut point is lossless the answer is zero."""
    import numpy as np

    from ate.frontier.compute import _first_loss

    volume = np.array([0.9, 0.5, 0.0])
    lost = np.array([1.0, 0.6, 0.2])  # never reaches zero
    assert _first_loss(volume, lost, 3) == pytest.approx(0.0)


def test_replicate_statistics_with_no_positives_are_degenerate():
    import numpy as np

    from ate.frontier.compute import _replicate_statistics

    signal = np.array([3.0, 2.0, 1.0])
    assert _replicate_statistics(signal, np.zeros(3, dtype=bool)) == (0.0, 0.5)


def test_bootstrap_with_one_class_absent_returns_degenerate_intervals(config):
    import numpy as np

    from ate.frontier.compute import _bootstrap

    signal = np.linspace(0, 1, 200)
    first, separation = _bootstrap(signal, np.zeros(200, dtype=bool), config)
    assert first == (0.0, 0.0)
    assert separation == (0.5, 0.5)
    first, separation = _bootstrap(signal, np.ones(200, dtype=bool), config)
    assert separation == (0.5, 0.5)


@pytest.mark.parametrize(
    "transform, name",
    [
        (lambda x: np.exp(x / 2), "exponential"),
        (lambda x: 1 / (1 + np.exp(-x)), "logistic, bounded to 0 and 1"),
        (lambda x: x**3, "cubic"),
        (lambda x: 100 * (1 / (1 + np.exp(-x))), "a 0 to 100 confidence score"),
        (lambda x: np.round(10 * (1 / (1 + np.exp(-x)))), "a discrete 0 to 10 score, with heavy ties"),
    ],
)
def test_separation_is_invariant_under_a_monotone_transform(config, alerts_factory, transform, name):
    """The corpus generator draws signals from two shifted normals, which is a
    textbook model and not how real alert signals are distributed. This is why
    that does not undermine the published numbers.

    Separation is a rank statistic, so it is unchanged by any strictly
    increasing transform of the signal. A real signal that is log normal,
    bounded, or a rounded 0 to 10 score has the same separation as the normal
    one it is a transform of, and the frontier curve has the same shape.
    """
    frame = alerts_factory(alerts=6_000, true_positives=120, shift=1.4, seed=41)
    baseline = rule_frontier(frame, "r", config)

    transformed = frame.copy()
    transformed["signal"] = transform(frame["signal"].to_numpy())
    result = rule_frontier(transformed, "r", config)

    # Ties from rounding move the statistic slightly; everything else is exact.
    tolerance = 0.02 if "discrete" in name else 1e-9
    assert result.separation == pytest.approx(baseline.separation, abs=tolerance), name
    assert result.volume_removed_at_first_loss == pytest.approx(
        baseline.volume_removed_at_first_loss, abs=tolerance
    ), name
    assert result.verdict is baseline.verdict, name


def test_an_inverted_transform_flips_the_separation(config, alerts_factory):
    """A decreasing transform is the configuration error case: the signal still
    carries exactly as much information, pointing the wrong way."""
    frame = alerts_factory(alerts=6_000, true_positives=120, shift=1.4, seed=41)
    baseline = rule_frontier(frame, "r", config)

    inverted = frame.copy()
    inverted["signal"] = -frame["signal"]
    result = rule_frontier(inverted, "r", config)

    assert result.separation == pytest.approx(1.0 - baseline.separation, abs=1e-9)
    assert not result.tunable
