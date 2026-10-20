# Generate signals from something other than two shifted normals
labels: enhancement

The corpus generator draws each alert's signal from a standard normal, shifted
up for true positives. ADR-003 states this plainly: it is a textbook model, not
a claim about how real alert signals are distributed.

Real signals are often bounded, heavily skewed, or multimodal. A vendor
confidence score is bounded to 0 to 100 and piles up at round numbers. A byte
count is log normal with a long tail.

## What to do

- Add a `distribution` field to the rule specification: `normal`, `lognormal`, `bounded`, `discrete`.
- Keep the shift parameterisation so the declared separation stays interpretable.
- Add a test that the frontier shape is still recovered correctly under each.

## What this will not change

Any published number materially. The frontier is a rank statistic and the
separation statistic is distribution free, so both are invariant under monotone
transforms of the signal. That is worth asserting as a test in its own right,
and is probably the most interesting part of this issue.
