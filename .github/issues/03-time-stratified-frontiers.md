# Compute the frontier per time window
labels: enhancement

A rule's signal distribution drifts. A tuning that was safe in January may not
be safe in June, and a single frontier over a year averages that away.

## What to do

- Accept an optional timestamp column, used only for bucketing and never read otherwise.
- Compute a frontier per bucket and report how separation moves across them.
- Flag rules whose separation is falling, which are the rules whose tuning is about to start costing more than it did.

## Note on the detection minimum

Bucketing divides the detections. A rule with 40 detections over a year has
fewer than the minimum in every month, so most rules will read unmeasured per
bucket. The report needs to say that clearly rather than showing a wall of
unknowns, and the right default bucket may be a quarter rather than a month.

## Why it matters

This is the first thing the README's "first metric to watch" section asks for,
and the tool cannot currently produce it.
