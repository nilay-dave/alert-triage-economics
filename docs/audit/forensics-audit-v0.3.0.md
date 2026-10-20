# Forensics audit: alert-triage-economics at v0.3.0

Four personas, each auditing independently, then an integrated verdict. Graded
PASS, WEAK or FAIL. Every FAIL found during this audit was fixed with its own
commit before delivery, and the fix commits are named below.

## Persona 1: The Principal Engineer

| # | Question | Grade | Justification |
| --- | --- | --- | --- |
| 1 | Clone, run, verify | PASS after a fix | Tested literally in a clean directory from the README text alone. `make verify` failed with `ModuleNotFoundError: No module named 'numpy'` while `pytest` run directly passed, because the console scripts pip installs bind to whichever interpreter installed them. Fixed in `fix(build): run every tool through an explicit interpreter`, then re-tested: 124 tests pass with no network, no credentials and no containers. |
| 2 | Architecture and design decisions | PASS | Three packages with a real boundary: `corpus` declares and generates, `frontier` computes, `report` renders. The statistics are separated from the rollup, which is why the per rule frontier is testable against worked examples independently of the stream level numbers. Five ADRs, each with rejected options. |
| 3 | Abstraction and configurability | PASS | Every tunable on `Config` from the environment with validation: minutes per alert, resample count, confidence, noise cap, minimum volume, detection minimum. The detection minimum in particular is configuration rather than a constant, so a team can lower it and own the consequence. |
| 4 | Error handling and edge cases | PASS | Nine documented failure modes. The interesting ones are the degenerate statistical cases: a rule with no detections, a rule below the detection minimum, a constant signal. Each has a distinct tested path and each resolves conservatively. |
| 5 | Testing | PASS | 124 tests, 99.3 percent branch coverage. The statistics have worked example tests small enough to check by hand, which is a convention in CONTRIBUTING rather than an accident, and it is what found the `_first_loss` direction bug. |

## Persona 2: The UX Director and Product Thinker

| # | Question | Grade | Justification |
| --- | --- | --- | --- |
| 1 | First 30 seconds | PASS | Opens with the claim it refutes and the number that refutes it. The bolded one liner states the cost of halving volume, which is the whole proposition. |
| 2 | The So What of results | PASS | Every figure is expressed as a consequence: volume removed against detections lost, free volume converted to analyst hours at a stated rate, untunable volume as a share of the stream. The reader is never handed a statistic without its unit of decision. |
| 3 | Visual storytelling | PASS | The frontier chart is the repository. It draws the no information diagonal, so a rule being tuned at random is visible rather than inferred, and the three verdicts are distinguished by line style and label as well as colour. Contrast on every colour pair is measured by a tool that parses the template, and runs in CI. |
| 4 | Actionability and handoff | PASS | The gate verb turns the analysis into a CI check. Future Work names the first metric to watch after deploying and explains why the obvious one, volume, is the wrong choice. |

## Persona 3: The Hiring Manager

| # | Question | Grade | Justification |
| --- | --- | --- | --- |
| 1 | Tutorial smell test | PASS | The problem is a specific sentence that appears on a great many SOC resumes, including the author's own, and the repository says so. Nothing about it is a textbook exercise. |
| 2 | Stolen Valor check | PASS after a fix | Was a FAIL. `scipy` was declared in `pyproject.toml` and listed in the README tech stack, and nothing imported it: the rank statistics are two lines of numpy. Removed in `fix(deps): drop scipy, which was declared and never imported`. This was the second repository in the batch with that exact fault, so `tools/check_dependencies.py` now fails CI on any declared dependency nothing uses, with an explicit list for the genuinely indirect ones so pyarrow stays distinguishable from scipy. |
| 3 | Hardest problem solved | PASS | Two, and the second is the better one. A one character direction error returned exactly 0.0 for every rule, a value plausible enough to be rationalised rather than noticed. Then a CI threshold check exposed the tool reporting a no signal rule as tunable on six detections with a narrow interval, which the interval mechanism could not catch by construction. Both are written up with the measurement rather than the moral. |
| 4 | One thing I will remember | PASS | That the repository says its own earlier correct answer was luck. The twelve detection rule was reported untunable for a reason that did not hold, and the README now tells that story rather than the flattering version it told first. |

## Persona 4: The Sceptic (provenance)

Automated by `scripts/provenance_check.py`. Final run: **25 pass, 3 weak, 0 fail
across 28 checks.**

Two FAILs were found and fixed during this audit:

1. `scipy` declared and never imported. Fixed, and generalised into a CI check so the fault cannot recur in this repository or be shipped from it.
2. `make verify` failed on a fresh clone and ran a subset of CI, so a green local run did not imply a green build. Both fixed in the same commit.

The three remaining WEAKs, each with a reason:

- **36 commits against a 40 target.** The work is at real granularity and padding is detectable, so the count stands. It will exceed 40 through the issue backlog.
- **One commit subject at 73 characters.** One over the limit, in a fix commit whose body carries the detail. `tools/check_commit_subject.py` runs as a commit-msg hook so the count cannot grow; rewriting history to shorten one subject would invalidate every clone for a character.
- **Identity placeholders unresolved.** Expected: the repository was built before the GitHub account was known. `tools/set_identity.sh` binds every URL in one pass.

## Integrated verdict

**Overall portfolio score: 9 out of 10.**

The repository holds up to all four reads. What distinguishes it is that its two
most interesting findings are both the tool failing: a statistic that was
confidently wrong and a safety property that turned out to be luck. Both are
written up with the measurement that exposed them, and both produced a design
change rather than a patch.

It is a 9 and not a 10 for the same reason as every repository in this batch: it
has not been pushed. The Actions tab is not green because no run has happened,
the releases are local tags rather than GitHub Releases, and the package is
publish ready rather than published.

### Critical failures (do not ship)

None outstanding. Both FAILs found during this audit were fixed with their own
commits, named above, and the affected checks re-run.

### Impact multipliers

1. **Push and publish.** Green Actions tab, three GitHub Releases from the existing annotated tags, Pages live so the badge endpoints resolve, and the package on PyPI through trusted publishing.
2. **Run against a real labelled corpus.** Issue 01. Every number here is a simulation, labelled as one, and the rank invariance tests show the generator's distributional assumption is not load bearing. What a real corpus would test is whether real alert signals separate at all like these do, and the honest expectation is that they separate worse.
3. **Ship the multivariate frontier.** Issue 02. One signal per rule is the simplification that made v1 shippable, and combining two conditions is what a tuning engineer actually does. It is also the point where the bootstrap cost becomes a real design problem rather than an optimisation.

### Elevator pitch

Every SOC engineer has written "reduced alert volume by N percent" on a CV, and
the sentence is almost always incomplete, because nobody collects the second
half: and it cost us this many real detections. This tool computes that second
half from a labelled alert history, reporting for every candidate threshold what
it removes and what it costs, with an interval on everything and a CI gate so a
volume target gets costed before it ships. On the bundled corpus halving alert
volume costs 15.6 percent of detections, and one rule in eight turns out to have
too few detections for the tool to say anything about at all, which it reports
as unknown rather than guessing.
