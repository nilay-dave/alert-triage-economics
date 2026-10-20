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

## The three verdicts

`tunable`, `not_tunable`, `insufficient_evidence`. Three states, because two
cannot say the thing that most often needs saying.

**`tunable`** means the lower bound of the separation interval clears 0.5, and
the rule has at least the minimum number of detections. Not the point estimate:
a rule showing 0.54 on an interval of 0.38 to 0.69 has not demonstrated
anything.

**`not_tunable`** means there are enough detections to judge and the interval
does not clear chance. The signal is the problem. Fix the signal or accept the
volume.

**`insufficient_evidence`** means there are fewer detections than the minimum,
which defaults to 20. The answer is that we do not know, whatever the interval
reads. The window is the problem, not the signal.

### Why the third state exists

A bootstrap resamples the detections it has. With six of them it measures how
the statistic moves under reweighting those six, which is a real quantity and
not the one that matters: it has nothing to compare them against to notice they
are unrepresentative. If all six score high, every replicate scores high, and
the interval comes out narrow around a badly wrong estimate.

That is not hypothetical. The bundled corpus contains a rule with no signal at
all by construction. On a 200,000 alert window it holds six detections, and the
tool reported separation 0.804 with a 95 percent interval of 0.611 to 0.960.
Narrow, confident, clear of chance, and wrong.

[ADR-005](adr/adr-005-insufficient-evidence.md) has the sweep behind the
threshold: on a pure noise signal a tunable verdict came back 3 to 5 percent of
the time below 20 detections, and never at or above it.

### Why not collapse unmeasured into untunable

It would give the same safety behaviour and the wrong instruction. An untunable
rule needs a better signal, which is a redesign. An unmeasured rule needs a
longer window, which is an export. Telling an engineer the first when the second
is true sends them to rewrite a rule that may be perfectly good.

`insufficient_evidence` never reads as tunable, so the conservative direction
holds either way. Suppressing alerts is irreversible in a way that not
suppressing them is not.
