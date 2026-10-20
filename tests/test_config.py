import pytest

from ate.config import Config, ConfigError, load_config


def test_defaults_are_usable():
    config = load_config()
    assert config.minutes_per_alert > 0
    assert config.bootstrap_resamples >= 100
    assert 0.5 < config.confidence < 1.0


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"minutes_per_alert": 0}, "minutes_per_alert"),
        ({"minutes_per_alert": -3}, "minutes_per_alert"),
        ({"bootstrap_resamples": 99}, "bootstrap_resamples"),
        ({"confidence": 0.5}, "confidence"),
        ({"confidence": 1.0}, "confidence"),
        ({"min_rule_volume": 0}, "min_rule_volume"),
        ({"bootstrap_noise_cap": 99}, "bootstrap_noise_cap"),
    ],
)
def test_invalid_values_are_rejected(kwargs, message):
    with pytest.raises(ConfigError, match=message):
        Config(**kwargs)


def test_env_overrides_are_read(monkeypatch):
    monkeypatch.setenv("ATE_MINUTES_PER_ALERT", "12.5")
    monkeypatch.setenv("ATE_BOOTSTRAP_RESAMPLES", "500")
    monkeypatch.setenv("ATE_BOOTSTRAP_NOISE_CAP", "1000")
    config = load_config()
    assert config.minutes_per_alert == 12.5
    assert config.bootstrap_resamples == 500
    assert config.bootstrap_noise_cap == 1000


def test_non_numeric_env_is_rejected(monkeypatch):
    monkeypatch.setenv("ATE_CONFIDENCE", "high")
    with pytest.raises(ConfigError, match="must be a number"):
        load_config()


def test_non_integer_env_is_rejected(monkeypatch):
    monkeypatch.setenv("ATE_BOOTSTRAP_RESAMPLES", "many")
    with pytest.raises(ConfigError, match="must be an integer"):
        load_config()
