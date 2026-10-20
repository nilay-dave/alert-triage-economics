# ADR-005: A third verdict for rules with too few detections

Status: accepted
Date: 2026-10-20

## Context

ADR-001 committed the tool to deciding tunability from the lower bound of a
bootstrap interval rather than from a point estimate. That is the right call and
it is not sufficient, which a CI threshold check exposed by accident.

The bundled corpus contains `ids_signature_generic`, a rule whose signal carries
no information about whether an alert is real. It is in the corpus specifically
so the tool has a chance to get it wrong. At 500,000 alerts it holds 12
detections, the tool reported it untunable, and that looked like the safety
property working.

Then the same rule was analysed on a 200,000 alert corpus, where it holds 6
detections:

```
separation 0.804, 95 percent interval [0.611, 0.960], verdict: tunable
```

A confident, narrow interval, comfortably clear of chance, on a rule whose true
separation is 0.5 by construction. The tool recommended tuning a rule that
cannot be tuned, and the interval gave no warning at all.

## Why the interval cannot catch this

A bootstrap resamples the observed data. With six detections it draws those same
six, over and over, in different multiplicities. It therefore measures how much
the statistic moves under reweighting of the observed sample, which is a real
quantity and not the one that matters here. What it cannot measure is whether
those six detections are representative of the rule, because it has nothing else
to compare them to. If all six happened to score high, every replicate scores
high, and the interval is narrow around a badly wrong estimate.

The earlier correct verdict at 12 detections was not the safety property
working. It was luck.

## What was measured

A signal with no information at all, 20,000 alerts, 60 independent draws per
detection count, asking how often the tool returned a tunable verdict:

| Detections | False tunable rate | Median interval width |
| --- | --- | --- |
| 3 | 5.0 percent | 0.600 |
| 5 | 3.3 percent | 0.458 |
| 8 | 3.3 percent | 0.397 |
| 12 | 3.3 percent | 0.316 |
| 20 | 0.0 percent | 0.247 |
| 30 | 0.0 percent | 0.202 |
| 50 | 0.0 percent | 0.160 |
| 100 | 0.0 percent | 0.114 |

A 3 to 5 percent false rate is, in one sense, exactly what a 95 percent interval
promises. That is the point: the promise is about long run coverage, and the
consequence here is that roughly one rule in twenty with a handful of detections
gets green lit for suppression. For a tool whose purpose is to stop people
deleting detections, that rate is not acceptable, and the fact that it is
statistically unsurprising does not make it safe.

## Options considered

1. **Widen the interval below some count.** Rejected as dishonest arithmetic:
   it reports an interval that is not the interval the method produced, chosen
   to force the answer the author wanted.
2. **Raise the confidence level for sparse rules.** Same objection, with extra
   steps, and it does not address the failure, which is that the sample may be
   unrepresentative rather than merely variable.
3. **Use a different interval method, such as BCa.** It corrects for bias and
   skewness, which helps at moderate counts and does not help at six, because
   the problem is information rather than method.
4. **Report untunable below a minimum count.** Rejected: it gives the right
   safety behaviour and the wrong instruction. An untunable rule needs a better
   signal. A rule with six detections needs a longer window. Telling an engineer
   the first when the second is true sends them to redesign a rule that may be
   perfectly good.
5. **Report a third verdict.** Chosen.

## Decision

Three verdicts: `tunable`, `not_tunable`, and `insufficient_evidence`. A rule
with fewer than `min_true_positives_for_verdict` detections is
`insufficient_evidence` regardless of what its interval reads, and
`insufficient_evidence` never reads as tunable.

The default is 20, taken from the measurement above as the smallest count at
which the false tunable rate was zero across the sweep. It is configuration
rather than a constant, because a team with a reason can lower it and own the
consequence.

## Consequences

The bundled corpus now reports zero untunable rules and one unmeasured one,
which is a more honest description of what 12 detections in 45,000 alerts
supports. The README was rewritten around that, because the previous version
cited the 12 detection rule as an example of the interval working, and that
example was luck rather than evidence.

The report, the chart and the CLI all carry three states. On the chart the
unmeasured rule is dash dotted and amber rather than dashed and grey, and its
label carries the detection count, so a reader sees immediately that the curve
is built from very little.

Collapsing the three back to two would be easy and is specifically what this
decision refuses. "We do not know" is an answer, and a tool that cannot say it
will eventually say something worse.

Two tests pin this: one reproduces the exact six detection case and requires an
unmeasured verdict, and one sweeps twelve seeds at 25 detections on a pure noise
signal and requires that none of them come back tunable.
