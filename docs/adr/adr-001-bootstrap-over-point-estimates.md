# ADR-001: Bootstrap intervals rather than point estimates

Status: accepted
Date: 2026-10-20

## Context

This tool exists to replace a sentence: "we reduced false positives by 60
percent". The problem with that sentence is not the 60 percent, it is that it
is reported alone, with no statement of what it cost or how certain it is.
Replacing it with a different bare number would reproduce the same error with
better arithmetic.

The arithmetic matters here more than it does in most places. A SOC's alert
stream is severely imbalanced: the bundled corpus runs at roughly one true
positive per 300 alerts, which is deliberately in the range public SOC reporting
describes. One rule in that corpus produces 45,000 alerts and 12 true positives.

Every statistic this tool computes about that rule is a statistic about twelve
observations.

## Options considered

1. **Point estimates only.** Report separation as 0.537 and removable volume as
   12.7 percent. Rejected: both figures are computed from twelve true positives
   and a reader has no way to see that. The 12.7 percent figure in particular is
   dangerous, because it looks like a tuning opportunity on a rule that has no
   usable signal at all.
2. **A normal approximation interval.** Cheap, and wrong at these counts: the
   sampling distribution of a rank statistic on twelve positives is not
   symmetric and the approximation produces intervals that extend past the
   statistic's own range.
3. **Analytic intervals for the rank statistic.** Available for the separation
   statistic, which is the Mann Whitney U, but not for the removable volume
   figure, which is an order statistic of the positive class with no convenient
   closed form. Two different interval methods in one table would invite the
   reader to compare numbers that are not comparable.
4. **Stratified bootstrap percentile intervals for both.** Chosen.

## Decision

Report a bootstrap percentile interval alongside every published statistic, and
decide tunability from the interval rather than the point estimate. A rule is
reported tunable only when the lower bound of its separation interval clears
0.5, which is the value a signal carrying no information would produce.

Resampling is stratified: true positives and noise alerts are resampled within
their own classes, so every replicate holds the same number of true positives as
the original.

## Consequences

The stratification is not a refinement, it is a requirement. An unstratified
bootstrap on a rule with twelve true positives draws replicates containing zero
of them with probability around 0.0000006 per replicate, which sounds negligible
until you consider that replicates with one or two positives are common, and in
those the separation statistic is defined but meaningless. The interval would
then describe the resampling procedure rather than the rule.

Deciding tunability from the lower bound makes the tool conservative in the
direction that matters. The bundled corpus contains a rule whose point estimate
for removable volume is 12.7 percent, which reads as a real opportunity, while
its separation interval runs from 0.38 to 0.69 and straddles chance. Acting on
the point estimate would mean suppressing 12.7 percent of a rule's volume on the
strength of where twelve detections happened to land.

The cost is runtime: every statistic is computed 2000 times instead of once.
ADR-002 covers what was done about that.

The confidence level and resample count are configuration rather than constants,
because a reader who wants a 99 percent interval should get one without editing
the source.
