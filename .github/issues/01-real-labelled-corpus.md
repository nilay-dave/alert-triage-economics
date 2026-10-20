# Run against a real labelled alert corpus
labels: enhancement,help wanted

Every number this repository publishes comes from a synthetic corpus. That is
labelled honestly everywhere it appears and ADR-003 explains why it is
synthetic, but a real number would be worth more than an honest simulation.

## What to do

Find a team willing to export three columns, `rule`, `signal` and
`is_true_positive`, from a quarter of their alert history under an NDA, run the
analysis, and publish the shape of the result rather than the rules.

The export is deliberately narrow: three columns with no alert content, no
usernames and no hostnames, which is a much easier ask than it sounds.

## What to report

Not the rule names. The distribution of separation values, the share of rules
falling below the detection minimum, and the cost of halving volume. The
interesting question is whether real alert signals separate as cleanly as two
shifted normals, and the honest expectation is that they do not.

## Why it is not already done

It needs a relationship, not a commit.
