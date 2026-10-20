import pytest

from ate.corpus.spec import SpecError, load_spec


def test_bundled_spec_loads_and_shares_sum_to_one():
    spec = load_spec()
    assert len(spec.rules) >= 5
    assert abs(sum(r.share for r in spec.rules) - 1.0) < 1e-6


def test_bundled_spec_states_a_severe_imbalance():
    """A corpus with a comfortable true positive rate would make every rule look
    tunable and prove nothing. This asserts the imbalance stays severe."""
    rate = load_spec().overall_tp_rate
    assert rate < 0.01, f"overall true positive rate {rate} is too generous to be realistic"
    assert 1 / rate > 200


def test_bundled_spec_contains_an_untunable_rule():
    """Every corpus needs a rule whose signal carries no information, or the
    tool is being evaluated against data built to flatter it."""
    spec = load_spec()
    untunable = [r for r in spec.rules if not r.tunable]
    assert len(untunable) >= 1
    assert all(r.signal_tp_shift == 0.0 for r in untunable)


def test_tunable_property_follows_the_shift():
    spec = load_spec()
    for rule in spec.rules:
        assert rule.tunable == (rule.signal_tp_shift > 0.0)


def test_by_name_and_names():
    spec = load_spec()
    assert spec.by_name(spec.names[0]) is not None
    assert spec.by_name("nope") is None
    assert len(spec.names) == len(spec.rules)


def _write(tmp_path, body):
    path = tmp_path / "rules.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_spec_without_rules_is_rejected(tmp_path):
    with pytest.raises(SpecError, match="no 'rules'"):
        load_spec(_write(tmp_path, "other: {}\n"))


def test_shares_that_do_not_sum_to_one_are_rejected(tmp_path):
    body = "rules:\n  - {name: a, share: 0.4, tp_rate: 0.01, signal: s, signal_tp_shift: 1.0}\n"
    with pytest.raises(SpecError, match="must sum to 1.0"):
        load_spec(_write(tmp_path, body))


def test_duplicate_rule_names_are_rejected(tmp_path):
    body = (
        "rules:\n"
        "  - {name: a, share: 0.5, tp_rate: 0.01, signal: s, signal_tp_shift: 1.0}\n"
        "  - {name: a, share: 0.5, tp_rate: 0.01, signal: s, signal_tp_shift: 1.0}\n"
    )
    with pytest.raises(SpecError, match="duplicate rule name"):
        load_spec(_write(tmp_path, body))


def test_unnamed_rule_is_rejected(tmp_path):
    body = "rules:\n  - {share: 1.0, tp_rate: 0.01, signal: s, signal_tp_shift: 1.0}\n"
    with pytest.raises(SpecError, match="no name"):
        load_spec(_write(tmp_path, body))


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("share", 0.0, "share must be in"),
        ("share", 1.5, "share must be in"),
        ("tp_rate", 1.0, "tp_rate must be in"),
        ("tp_rate", -0.1, "tp_rate must be in"),
        ("signal_tp_shift", -1.0, "must not be negative"),
    ],
)
def test_out_of_range_values_are_rejected(tmp_path, field, value, message):
    values = {"name": "a", "share": 1.0, "tp_rate": 0.01, "signal": "s", "signal_tp_shift": 1.0}
    values[field] = value
    if field != "share":
        values["share"] = 1.0
    body = "rules:\n  - {" + ", ".join(f"{k}: {v}" for k, v in values.items()) + "}\n"
    with pytest.raises(SpecError, match=message):
        load_spec(_write(tmp_path, body))


def test_rule_without_a_signal_is_rejected(tmp_path):
    body = "rules:\n  - {name: a, share: 1.0, tp_rate: 0.01, signal: '', signal_tp_shift: 1.0}\n"
    with pytest.raises(SpecError, match="signal must be named"):
        load_spec(_write(tmp_path, body))


def test_empty_rule_list_is_rejected(tmp_path):
    with pytest.raises(SpecError):
        load_spec(_write(tmp_path, "rules: []\n"))
