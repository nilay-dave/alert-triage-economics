"""Generate a reproducible labelled alert corpus.

A portfolio repository cannot ship a real SOC's alert history: it contains
usernames, hostnames and the shape of a real organisation's detections. So the
corpus is synthetic, the generator is in the repository, and every figure
derived from it is labelled as a simulation.

What matters is that the corpus is honest about the thing being measured. Two
properties carry that:

1. **The imbalance is severe and stated.** Roughly 1 true positive per 300
   alerts overall, with per rule rates between 0.03 and 1.1 percent. A corpus
   with a comfortable 10 percent true positive rate would make every rule look
   tunable and the whole exercise would prove nothing.

2. **One rule has no frontier at all.** `ids_signature_generic` has a signal
   that carries no information about whether an alert is real, so no threshold
   on it removes noise faster than it removes detections. Any corpus where every
   rule can be tuned is a corpus built to flatter the tool.

The signal model is deliberately simple and stated rather than hidden: each
alert draws a standard normal signal value, and true positives draw from a
distribution shifted up by `signal_tp_shift` standard deviations. That is a
textbook two-population model. It is not a claim about how real alert signals
are distributed, and the README says so. What it buys is that the frontier the
tool computes has a known correct shape, so the tool can be checked against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ate.corpus.spec import CorpusSpec, load_spec
from ate.logging import get_logger

log = get_logger(__name__)

CHUNK_ROWS = 250_000


@dataclass(frozen=True)
class GenerationResult:
    path: Path
    alerts: int
    true_positives: int
    seed: int
    per_rule: dict[str, tuple[int, int]]

    @property
    def overall_tp_rate(self) -> float:
        return self.true_positives / self.alerts if self.alerts else 0.0


def generate(
    out_path: Path | str,
    alerts: int,
    seed: int = 7,
    spec: CorpusSpec | None = None,
) -> GenerationResult:
    """Write `alerts` labelled alerts to a parquet file at `out_path`."""
    if alerts <= 0:
        raise ValueError(f"alerts must be positive, got {alerts}")

    spec = spec or load_spec()
    rng = np.random.default_rng(seed)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    shares = np.array([rule.share for rule in spec.rules])
    tp_rates = np.array([rule.tp_rate for rule in spec.rules])
    shifts = np.array([rule.signal_tp_shift for rule in spec.rules])
    names = np.array(spec.names)

    frames: list[pd.DataFrame] = []
    per_rule: dict[str, list[int]] = {name: [0, 0] for name in spec.names}
    written = 0

    while written < alerts:
        size = min(CHUNK_ROWS, alerts - written)
        index = rng.choice(len(spec.rules), size=size, p=shares)
        is_tp = rng.random(size) < tp_rates[index]
        # Standard normal signal, shifted up for true positives by that rule's
        # separation. A shift of zero means the signal is pure noise.
        signal = rng.standard_normal(size) + np.where(is_tp, shifts[index], 0.0)

        frames.append(
            pd.DataFrame(
                {
                    "rule": pd.Categorical(names[index], categories=spec.names),
                    "signal": signal.astype(np.float32),
                    "is_true_positive": is_tp,
                }
            )
        )
        for position, name in enumerate(spec.names):
            mask = index == position
            per_rule[name][0] += int(mask.sum())
            per_rule[name][1] += int(is_tp[mask].sum())
        written += size

    frame = pd.concat(frames, ignore_index=True)
    frame.to_parquet(out_path, compression="zstd", index=False)

    result = GenerationResult(
        path=out_path,
        alerts=int(len(frame)),
        true_positives=int(frame["is_true_positive"].sum()),
        seed=seed,
        per_rule={name: (counts[0], counts[1]) for name, counts in per_rule.items()},
    )
    log.info(
        "corpus generated",
        extra={
            "alerts": result.alerts,
            "true_positives": result.true_positives,
            "tp_rate": round(result.overall_tp_rate, 6),
            "path": str(out_path),
            "seed": seed,
        },
    )
    return result
