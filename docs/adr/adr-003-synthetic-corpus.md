# ADR-003: Ship a synthetic corpus, and put a rule in it that cannot be tuned

Status: accepted
Date: 2026-10-20

## Context

This tool needs labelled alerts: alerts where somebody has recorded whether each
one was a real detection. That data is the most sensitive thing a SOC holds. It
contains usernames, hostnames, the shape of an organisation's detections, and
the record of which attacks got through. No portfolio repository can ship it.

The options are therefore a public dataset, a corpus derived from one, or a
generated corpus.

## Options considered

1. **A public intrusion detection dataset** such as the CIC or UNSW families.
   Rejected for this specific purpose. Those datasets label network flows as
   attack or benign, which is a different question from whether a SOC alert was
   worth an analyst's time, and their class balance is nothing like a real alert
   queue because they were built to train classifiers rather than to describe a
   triage workload.
2. **A corpus derived from public honeypot or malware feeds.** Rejected: the
   labels describe the sample, not an analyst's disposition of an alert, so the
   derivation would be inventing the labels while appearing not to.
3. **A generated corpus with the generator in the repository.** Chosen.

## Decision

Generate the corpus from a declared specification that ships in the repository,
seeded for reproducibility, and label every figure derived from it as a
simulation at the point it is published, including in badges.

Two properties of the specification are load bearing and neither is incidental.

**The imbalance is severe and stated.** Roughly one true positive per 300 alerts
overall, with per rule rates between 0.03 and 1.1 percent. A corpus with a
comfortable 10 percent true positive rate would make every rule look tunable and
the whole exercise would prove nothing. A test asserts the rate stays below one
percent, so the corpus cannot drift comfortable.

**One rule has no frontier at all.** `ids_signature_generic` has a signal that
carries no information about whether an alert is real. No threshold on it
removes noise faster than it removes detections. A test asserts the bundled
specification still contains such a rule.

## Consequences

The second property is the one worth defending in an interview. A corpus where
every rule can be tuned is a corpus built to flatter the tool, and a tool
evaluated only against flattering data will confidently recommend tuning rules
that should not be tuned. The untunable rule is in the corpus specifically so
that the tool has an opportunity to get it wrong, and the test that asserts the
rule is reported untunable is the most valuable test in the repository.

It also happens to produce the most useful output the tool generates. That rule
reports a removable volume of 12.7 percent, which looks like an opportunity, on
the strength of twelve detections. Only the interval reveals it. That single
contrast is the argument for ADR-001 made concrete, and it would not exist if
the corpus had been built to be tuned successfully.

The honest limitation: the signal model is two normal distributions, one
shifted. That is a textbook model, not a claim about how real alert signals are
distributed, which are often bounded, skewed or piled up on round numbers.

It matters less than it first appears, and that is worth being precise about
rather than waving away. Both published statistics are rank based: separation is
the normalised Mann Whitney U, and removable volume is a position in the sorted
order. Neither changes under any strictly increasing transform of the signal. A
real signal that is log normal, or bounded to 0 and 1, or rounded to a 0 to 10
confidence score, has the same separation as the normal variate it is a
transform of, and its frontier has the same shape.

So the normality of the generator is not load bearing for anything the tool
publishes. `tests/test_frontier.py::test_separation_is_invariant_under_a_monotone_transform`
asserts this across five transforms including a heavily tied discrete score,
rather than leaving it as a claim in a document.

What does change under a real distribution is the relationship between a
threshold and a volume, which is why the report shows thresholds on the curve in
the signal's own units and never interprets them.

A real corpus would still be more faithful, and the roadmap records running
against one as the next step.
