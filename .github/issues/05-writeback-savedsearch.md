# Emit SIEM tuning diffs from a chosen point on the frontier
labels: enhancement

The tool reports what each threshold costs. Shipping the chosen one is still
manual: someone reads the number, opens the SIEM, and edits a rule.

## What to do

- `ate emit --rule X --cut 0.3 --format splunk` writing a savedsearch diff, and `--format sigma` writing a filter block.
- Include the cost in a comment in the generated diff, so the reviewer sees what it buys and what it loses without leaving the pull request.

## The constraint that must not be broken

The tool emits a diff for a human to review. It does not apply it. The README's
Intentionally out of scope section says the tool never picks a threshold, and
writing back is not picking, but the line is thin and a PR that adds an
`--apply` flag will be declined.

## Trigger

Once the frontier has been used to ship real tunings and the diffs are being
written by hand anyway.
