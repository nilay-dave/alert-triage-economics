"""Load and validate the alert corpus specification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_SPEC = Path(__file__).parent / "rules.yml"


class SpecError(ValueError):
    """Raised when the corpus specification cannot be used."""


@dataclass(frozen=True)
class RuleSpec:
    name: str
    share: float
    tp_rate: float
    signal: str
    signal_tp_shift: float
    note: str = ""

    @property
    def tunable(self) -> bool:
        """False when the rule's signal carries no information about truth.

        A rule whose signal does not separate true positives from noise has no
        frontier: every threshold that removes volume removes detections at the
        same rate. Reporting one anyway would be the dishonest version of this
        tool.
        """
        return self.signal_tp_shift > 0.0


@dataclass(frozen=True)
class CorpusSpec:
    rules: tuple[RuleSpec, ...]

    def by_name(self, name: str) -> RuleSpec | None:
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(rule.name for rule in self.rules)

    @property
    def overall_tp_rate(self) -> float:
        """Weighted true positive rate across the whole stream."""
        return sum(rule.share * rule.tp_rate for rule in self.rules)


def load_spec(path: Path | str | None = None) -> CorpusSpec:
    spec_path = Path(path) if path else DEFAULT_SPEC
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "rules" not in raw:
        raise SpecError(f"{spec_path} has no 'rules' list")

    rules: list[RuleSpec] = []
    seen: set[str] = set()
    for entry in raw["rules"]:
        name = str(entry.get("name", "")).strip()
        if not name:
            raise SpecError("a rule has no name")
        if name in seen:
            raise SpecError(f"duplicate rule name: {name}")
        seen.add(name)

        share = float(entry.get("share", 0.0))
        tp_rate = float(entry.get("tp_rate", 0.0))
        shift = float(entry.get("signal_tp_shift", 0.0))
        if not 0.0 < share <= 1.0:
            raise SpecError(f"{name}: share must be in (0, 1], got {share}")
        if not 0.0 <= tp_rate < 1.0:
            raise SpecError(f"{name}: tp_rate must be in [0, 1), got {tp_rate}")
        if shift < 0.0:
            raise SpecError(f"{name}: signal_tp_shift must not be negative, got {shift}")
        if not str(entry.get("signal", "")).strip():
            raise SpecError(f"{name}: signal must be named")

        rules.append(
            RuleSpec(
                name=name,
                share=share,
                tp_rate=tp_rate,
                signal=str(entry["signal"]).strip(),
                signal_tp_shift=shift,
                note=str(entry.get("note", "")).strip(),
            )
        )

    if not rules:
        raise SpecError(f"{spec_path} declares no rules")
    total = sum(rule.share for rule in rules)
    if abs(total - 1.0) > 1e-6:
        raise SpecError(f"rule shares must sum to 1.0, got {total:.6f}")
    return CorpusSpec(rules=tuple(rules))
