# alert-triage-economics

"We reduced false positives by 60 percent" is one of the most common sentences
in SOC reporting and one of the least often costed. The sentence has a second
half that nobody collects: and it cost us this many real detections.

This tool computes that second half. Feed it a labelled alert stream and it
reports, per rule, what every candidate threshold would have removed and what it
would have cost.

## Start here

- [Reading the frontier](reading-the-frontier.md) explains the chart and what each shape means.
- [The statistics](statistics.md) covers separation, intervals, and the three verdicts, including why "we do not know" needed to be one of them.
- The [example report](report.html) is regenerated on every docs deploy from the bundled synthetic corpus.

## Install

```bash
pip install alert-triage-economics
```

## The shortest useful run

```bash
ate generate --alerts 500000 --out alerts.parquet --seed 7
ate frontier --alerts alerts.parquet --out report.html
```

The first command exists so the tool can be evaluated without exporting
anything real. Replace it with your own three column export, `rule`, `signal`
and `is_true_positive`, and the numbers stop being a simulation.

## Decisions

- [ADR-001](adr/adr-001-bootstrap-over-point-estimates.md): why every statistic ships with an interval.
- [ADR-002](adr/adr-002-capped-noise-pool.md): capping the resampled noise pool, with the measurement.
- [ADR-003](adr/adr-003-synthetic-corpus.md): the synthetic corpus, and the rule in it that cannot be tuned.
- [ADR-004](adr/adr-004-which-number-to-lead-with.md): leading with the stable number rather than the intuitive one.
- [ADR-005](adr/adr-005-insufficient-evidence.md): the third verdict, and the measurement behind its threshold.
