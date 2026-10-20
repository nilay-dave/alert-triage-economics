# Offer BCa intervals as an option
labels: enhancement,good first issue

Intervals are percentile bootstrap. BCa corrects for bias and skewness and is
generally better behaved at moderate sample sizes.

## What to do

- Add `ATE_INTERVAL_METHOD` with `percentile` and `bca`.
- Implement BCa: the acceleration term needs a jackknife over the positive class, which is cheap because that class is small by construction.
- Report which method produced an interval, in the JSON and in the report footer.

## What this will not fix

ADR-005's failure. BCa corrects the shape of the interval, not the fact that six
detections cannot tell you whether six detections are representative. The
detection minimum stays either way, and a PR that removes it on the grounds that
BCa is better will be declined.

## Why this is a good first issue

Self contained, the jackknife is a dozen lines, and `tests/test_frontier.py`
shows exactly how an interval gets asserted.
