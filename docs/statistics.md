# The statistics

Three numbers per rule, each with an interval. This page says what they are,
how they are computed, and where each one breaks.

## Separation

The probability that a randomly chosen true positive scores higher on the tuning
signal than a randomly chosen noise alert.

This is the Mann Whitney U statistic normalised by the product of the class
sizes, which is the same quantity as the area under an ROC curve. It is computed
from ranks rather than by sampling pairs, so it is exact rather than estimated:

```
U = rank_sum(positives) - n_pos * (n_pos + 1) / 2
separation = U / (n_pos * n_neg)
```

0.5 means the signal carries no information about whether an alert is real. 1.0
means it separates perfectly. Below 0.5 means the signal is inverted, which is a
real finding and usually a configuration error.

**Where it breaks.** It says nothing about where on the curve the separation
lives. Two rules can share a separation of 0.75 while one allows a generous free
cut and the other does not. Read it with the chart, never instead of it.

## Removable free volume

The largest share of a rule's volume that can be removed while losing zero true
positives. Equivalently: everything scoring below the lowest scoring detection.

**Where it breaks.** It is an order statistic of the minimum, so it depends on
how long the window is. More detections means a lower worst one means a smaller
figure. On a fixed stream it fell from 17.3 to 2.7 percent as the corpus grew
from 50,000 to 2,000,000 alerts. [ADR-004](adr/adr-004-which-number-to-lead-with.md)
has the measurement and is the reason this is not the headline number.

It is still the right answer to "what can we remove from this export today".

## Blanket cut cost

The share of true positives lost if a flat percentage of every rule's volume is
removed, including the rules that cannot be tuned.

This is the number that answers a volume reduction target. It is stable across
window lengths, which is why the report leads with it.

**Where it breaks.** It assumes the cut is applied uniformly, which is a
deliberately pessimistic model of how tuning is actually done. A team tuning
rule by rule, guided by the frontier, will do better than this figure. It is the
cost of the blunt version of the instruction, and the blunt version is what a
volume target usually becomes.

## The intervals

Every published statistic carries a bootstrap percentile interval, by default
2000 stratified replicates at 95 percent.

**Stratified** means true positives and noise alerts are resampled within their
own classes, so every replicate holds the same number of detections as the
original. This is a requirement rather than a refinement: an unstratified
bootstrap on a rule with twelve detections produces replicates holding one or
two, where the statistics are defined but meaningless, and the resulting interval
describes the procedure rather than the rule.

**The noise pool is capped** at 20,000 draws per replicate. Both statistics have
sampling variance dominated by the detection count, so the cap discards precision
the result could never have used.
[ADR-002](adr/adr-002-capped-noise-pool.md) has the table, and a test asserts the
claim rather than leaving it to the document.

## Tunability

A rule is reported tunable when the lower bound of its separation interval
clears 0.5.

Not the point estimate. The bundled corpus contains a rule whose point estimate
is 0.537 and whose interval runs 0.378 to 0.691, on twelve detections in 45,000
alerts. Its removable free volume reads 12.7 percent, which looks like a real
opportunity and is an artefact of where twelve observations happened to land.

Deciding from the lower bound makes the tool conservative in the direction that
matters: it will call a tunable rule untunable before it calls an untunable rule
tunable. Suppressing alerts is irreversible in a way that not suppressing them
is not.
