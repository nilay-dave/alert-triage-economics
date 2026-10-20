# ADR-004: Lead with the blanket cut cost, not the free volume

Status: accepted
Date: 2026-10-20

## Context

The tool produces two headline candidates and the obvious one is wrong.

**Free volume** is the share of a rule's alerts removable without losing a
single detection. It is the number a SOC lead wants, it is intuitive, and it is
what the first version of this README led with.

**Blanket cut cost** is the share of true positives lost if a flat percentage of
every rule's volume is removed. It is less intuitive and it is the number that
actually refutes an uncosted tuning claim.

The benchmark across three corpus sizes exposed the problem:

| Corpus | Free volume | Cost of halving |
| --- | --- | --- |
| 50,000 alerts | 17.3 percent | 16.8 percent |
| 500,000 alerts | 6.5 percent | 15.6 percent |
| 2,000,000 alerts | 2.7 percent | 16.2 percent |

Free volume moved by a factor of six across the same stream. The cost of halving
barely moved at all.

## Why free volume is unstable

It is an order statistic of the minimum. Free volume is determined entirely by
where the single lowest scoring true positive in the window happens to sit:
every alert below it is removable, and nothing below it is. A longer window
contains more detections, so it contains a lower worst one, so the figure
shrinks. Isolated on a single rule with the separation and true positive rate
held fixed:

| Window | True positives | Separation | Free volume |
| --- | --- | --- | --- |
| 5,000 | 20 | 0.802 | 11.9 percent |
| 20,000 | 80 | 0.816 | 7.5 percent |
| 100,000 | 400 | 0.845 | 4.7 percent |
| 400,000 | 1,600 | 0.848 | 2.6 percent |

Separation is stable to three decimal places. Free volume falls by a factor of
four and would keep falling, because the minimum of a sample has no limit other
than the support of the distribution.

This is not a bug in the computation. It is the statistic answering exactly the
question it was asked, and the question containing a hidden dependence on how
long you watched.

## Options considered

1. **Lead with free volume anyway.** Rejected once the benchmark showed it
   moving by a factor of six on the same stream. A headline figure that depends
   on the export window is a figure a reader will quote in one meeting and be
   contradicted on in the next.
2. **Drop free volume.** Rejected: it is the right answer to "what can we remove
   today", which is a real question, and it is correct for the window it was
   computed on.
3. **Report free volume at a fixed window.** Rejected as a false fix. Fixing the
   window makes the figure comparable between runs while leaving it arbitrary,
   and hides the dependence rather than disclosing it.
4. **Lead with the blanket cut cost, keep free volume with its caveat.** Chosen.

## Decision

The README, the report and the badge lead with the cost of halving volume. Free
volume stays in the report, in the tiles rather than the headline, and the
window dependence is stated wherever it appears.

## Consequences

The headline is now the number that does the work this tool was built for. "We
cut alert volume in half" is the claim; "that costs 15.6 percent of your
detections" is the reply, and it is a reply that holds whether the analysis ran
on a week or a quarter.

Free volume keeps its interval, which already communicated some of this: on the
500,000 alert corpus the interval on one rule runs from 1.1 to 13.9 percent,
which is a reader's clue that the point estimate is soft. The interval captures
sampling variation at a fixed window, though, not the window dependence itself,
so the caveat is written out rather than left to the interval.

A test asserts the direction: free volume must not increase as the window grows
on a stream with fixed properties. If a change ever makes free volume look
stable, something has been smoothed over.

The honest framing for anyone reading the output: free volume says what is
removable from this export. The blanket cut cost says what tuning costs. Only
the second one is a property of the detections rather than of the window.
