# Derive the detection minimum from power rather than a sweep
labels: enhancement

ADR-005 sets the minimum at 20 detections, taken from the smallest count at
which a sweep over 60 draws produced no false tunable verdicts on a pure noise
signal.

That is an empirical answer to a question with an analytic one. The separation
statistic is the Mann Whitney U, whose null distribution is known, so the count
needed for a given false positive rate at a given confidence level can be
derived rather than measured.

## What to do

- Derive the minimum from the target false tunable rate and the configured confidence level.
- Make it the default, keeping the explicit override.
- Keep the sweep as a test that the derived value behaves, because a derivation that disagrees with the measurement is a derivation with a mistake in it.

## Why the empirical number shipped first

It is defensible, it is measured, and it is stated as measured. Replacing it
with a derivation is an improvement in rigour rather than a correction.
