# Contributing

## Getting set up

```bash
git clone https://github.com/nilay-dave/alert-triage-economics.git
cd alert-triage-economics
python -m venv .venv && source .venv/bin/activate
make install
make verify
```

`make verify` runs every check CI runs, in the same order: lint, tests with
coverage, the dependency check, the report contrast check and the provenance
audit. A verify that is a subset of CI is a verify that lies, so if it passes
locally the build should be green.

It needs no network, no API keys and no containers. If it does not pass on a
clean checkout, that is a bug worth an issue on its own.

Everything runs through `$(PYTHON)`, which defaults to `python3`. The console
scripts pip installs bind to whichever interpreter installed them, which on a
machine with several Pythons is not necessarily the one on PATH. Override it if
you need to: `make verify PYTHON=python3.12`.

## The rules that matter here

**Verify before you commit, as two separate steps.** Run the tests, read the
output, then commit. Do not chain `pytest && git commit`: if the suite fails for
a reason you have not read yet, the commit lands anyway and the history stops
being trustworthy.

**Never publish a statistic without an interval.** This repository exists
because a bare number was treated as a finding. Any new statistic needs a
bootstrap interval and any new decision needs to be made from the interval, not
the point estimate. See ADR-001.

**Every published number is measured.** Numbers in the README and in `docs/` are
tagged with `<!--number:path-->` markers and checked against `docs/metrics.json`
by `tools/check_numbers.py` in CI. If a change moves a number, run `make report`
and update the document in the same commit. Do not edit `docs/metrics.json` by
hand.

**Numbers from the bundled corpus are labelled as simulations.** The corpus is
synthetic. Any figure derived from it says so at the point it is published,
including in badges.

**The corpus keeps its untunable rule.** `src/ate/corpus/rules.yml` contains a
rule whose signal carries no information, and a test asserts it is still there.
Removing it would make the tool look better and make it worse. See ADR-003.

**The tool reads three columns.** `rule`, `signal`, `is_true_positive`. A change
that reads alert content needs to be discussed in an issue first, because it
changes what a user has to export and therefore what they have to protect. See
SECURITY.md.

## Commit messages

Conventional Commits: `type(scope): imperative summary` under 72 characters, no
trailing period. Types in use: feat, fix, test, docs, ci, chore, refactor, perf,
build.

Fix commits carry a body with one line of symptom and one line of root cause.

No em dashes or en dashes anywhere, in code, comments, commit messages or docs.

## Adding a rule to the corpus

Rules live in `src/ate/corpus/rules.yml`. Set `share` so the shares still sum to
1.0, which the loader enforces, and set `tp_rate` so the overall imbalance stays
severe, which a test enforces. `signal_tp_shift` is how many standard deviations
higher the signal runs on true positives; zero means the rule cannot be tuned.

## Changing the statistics

Changes under `src/ate/frontier/` need a test that pins the behaviour against a
worked example small enough to check by hand, in the style of
`tests/test_frontier.py::test_curve_on_a_worked_example`. A statistic that only
has property tests can be confidently wrong in a way nobody notices.

## Pull requests

One concern per pull request. CI must be green. New behaviour needs a test; a
bug fix needs a regression test that fails before the fix.
