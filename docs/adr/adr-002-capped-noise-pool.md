# ADR-002: Cap the noise pool per bootstrap replicate

Status: accepted
Date: 2026-10-20

## Context

ADR-001 committed the tool to 2000 bootstrap replicates per rule. The first
implementation rebuilt the entire frontier curve inside each replicate in order
to read two numbers off it, and resampled the full noise class every time.

On the bundled corpus, eight rules at 2000 replicates took over 400 seconds. A
400 second analysis is one that gets run once and then not again, which defeats
the purpose of shipping it as a CI gate.

Two separate costs were at work. Rebuilding the curve sorts and accumulates over
the whole rule, when both statistics have closed forms that need one sort.
Resampling 100,000 noise alerts per replicate dominates that sort, when the
sampling variance of both statistics is driven by the positive count.

## Options considered

1. **Fewer replicates.** Rejected. The interval is the product here, and 200
   replicates gives a visibly lumpy percentile estimate at these counts.
2. **Parallelism.** Rejected for v1: it multiplies the hardware rather than
   removing the work, and the result stops being reproducible from a seed alone
   unless the work is partitioned carefully.
3. **Analytic interval for separation, bootstrap only for removable volume.**
   Rejected under ADR-001's reasoning: two interval methods in one table are not
   comparable.
4. **Compute both statistics directly and cap the resampled noise pool.** Chosen.

## Decision

Compute the two replicate statistics in closed form rather than from the curve,
and draw at most `bootstrap_noise_cap` noise alerts per replicate, defaulting to
20,000. The positive class is always resampled in full.

## What was measured

On a rule with 100,000 alerts and 238 true positives, 300 replicates each:

| Noise pool | Time | Separation interval | Width |
| --- | --- | --- | --- |
| Full, 99,762 | 3.93 s | [0.8117, 0.8608] | 0.0492 |
| 50,000 | 1.76 s | [0.8065, 0.8609] | 0.0544 |
| 20,000 | 0.67 s | [0.8114, 0.8591] | 0.0477 |
| 10,000 | 0.32 s | [0.8093, 0.8581] | 0.0488 |

The same comparison on a rule with 12 true positives produced interval widths of
0.2082 uncapped and 0.2211 at 20,000, against a point estimate uncertainty that
spans a third of the statistic's range.

The variation between cap levels is smaller than the variation between seeds at
the same cap, which is the test: the cap is not changing the answer, it is
changing how long the answer takes. A full run of eight rules at 2000 replicates
went from over 400 seconds to 34.

## Consequences

The justification is statistical rather than a shortcut, and it is worth stating
precisely: both statistics are functions of where the positive class sits within
the combined distribution. The noise class defines that distribution, and 20,000
draws estimate it to a precision far beyond what 12 to 465 positives can resolve.
Capping it discards precision the result could never have used.

This holds because the cap is large relative to the positive count. It would not
hold for a rule with tens of thousands of true positives, which is not a rule
anybody needs this tool for, and the cap is configuration rather than a constant
so that case can be handled by raising it.

A test asserts the claim directly rather than trusting this document: it computes
a frontier capped and uncapped on the same fixture and requires the interval
bounds to agree within 0.02.

The closed form statistics are a separate change bundled into the same decision.
A test asserts they produce exactly what the curve based path produces, because
the curve is the definition and the fast path is only an optimisation.
