# Reading the frontier

Each line is one rule. The x axis is the share of that rule's alert volume a
threshold would remove. The y axis is the share of that rule's true positives
that would go with it.

## The diagonal

The dotted diagonal is the reference that makes the rest of the chart mean
something: remove half the volume, lose half the detections. That is what tuning
a rule whose signal carries no information looks like. You are not tuning, you
are sampling.

Every rule should be read against it.

## Shapes and what they mean

**A line hugging the bottom left then rising late.** The signal separates well.
A large share of volume can go before detections start falling. This is a rule
worth tuning and the chart says where to stop.

**A line on or above the diagonal.** The signal is noise, or worse than noise if
it is above. Any threshold deletes detections at least as fast as it deletes
volume. Do not tune this rule; fix the signal or accept the volume.

**A staircase.** Few detections. Each step is one true positive dropping out, so
a rule with twelve of them has twelve steps. Staircases are a visual warning
that the curve is built from very little, and the interval in the table is where
to check how little.

**A line that bows well below the diagonal but starts rising immediately.** The
signal separates, but the lowest scoring detection sits low. Free volume will be
small even though the rule is genuinely tunable. This is the case where the
blanket cut figures are more useful than the free volume one.

## What the table adds

The chart shows shape. The table shows whether the shape is trustworthy.

**Separation** is the probability a random true positive outscores a random
noise alert. 0.5 is no information, 1.0 is perfect. It is the single number
summary of how far the line bows from the diagonal.

**The interval** on separation is what decides tunability. A rule can show a
point estimate of 0.54, which looks faintly promising, on an interval of 0.38 to
0.69, which includes chance. The bundled corpus contains exactly that rule, on
purpose.

**Removable free** is the volume removable with zero detections lost. Read it
with the caveat in [ADR-004](adr/adr-004-which-number-to-lead-with.md): it
depends on the length of the window, because it is determined by the single
lowest scoring detection in it. A longer export produces a smaller number for
the same rule.

**Lost at 50 percent** is stable across window lengths and is the figure to
quote when somebody proposes a volume target.

## The question the chart cannot answer

What an attacker would have done differently had the threshold been in place.
This is a replay: it says what would have happened to these alerts. Nothing
about a historical replay licenses a claim about future adversary behaviour, and
a tuning that looks free here can still change what gets attempted.
