# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-20

A third verdict, measured benchmarks, and the docs. This is the first release
whose published numbers are checked in CI.

### Added
- A third verdict, `insufficient_evidence`, for rules with fewer detections than the configured minimum. Below that count a bootstrap interval can be narrow and badly wrong, so the tool says it does not know rather than guessing. Measured at 20 detections: on a signal with no information at all, a tunable verdict came back 3 to 5 percent of the time below that count and never at or above it. ADR-005 has the table.
- `unmeasured_rules` and `unmeasured_volume_pct` on the stream summary, surfaced in the CLI, the report and the chart, because an unmeasured rule needs a longer window while an untunable one needs a better signal.
- Benchmark harness covering 50k, 500k and 2M alert corpora, with raw results in `benchmark/results/benchmark.json`.
- `tools/collect_metrics.py` and `tools/check_numbers.py`, which verify 29 published figures across the README and docs against measured values on every CI run.
- `tools/check_contrast.py`, which parses the report's colour tokens out of the template and computes the real WCAG ratios.
- MkDocs Material documentation site with a Pages deploy workflow.
- Coverage and headline-number badges fed from a JSON endpoint CI writes to `gh-pages`.
- Community health files, issue and PR templates, Dependabot, pre-commit hooks and a provenance audit of the repository's own signals.
- ADR-004 on which number to lead with, and ADR-005 on the third verdict.

### Changed
- The README, the report and the badge now lead with the cost of halving volume rather than the free volume figure. Free volume moved by a factor of six across corpus sizes on the same stream, because it is an order statistic of the minimum; the cost of halving barely moved. ADR-004 records the measurement.
- Verdict severity in the report no longer depends on colour: each one carries a glyph and a word.

### Fixed
- A rule with no detections in the window reported that nearly its whole volume was removable for free, because with nothing to lose every cut point is trivially lossless.
- Three tagged numbers in the README were never checked and the run still reported success, because the marker pattern cannot read an escaped dot. Metric keys now carry no dots, and any marker the pattern cannot parse is a failure rather than a skip.

### Performance
- Bootstrap replicates compute their two statistics in closed form rather than rebuilding the frontier curve, and the resampled noise pool is capped at 20,000 draws. Eight rules at 2000 replicates went from over 400 seconds to 34, with interval widths of 0.0477 capped against 0.0492 uncapped. ADR-002 has the comparison.

## [0.2.0] - 2026-10-20

The CLI, the charts and the report.

### Added
- `ate generate`, `ate frontier` and `ate gate`. The gate exits 2 when a proposed volume cut costs more detections than a configured budget.
- Frontier chart with the no-information diagonal drawn, so a rule being tuned at random is visible rather than inferred.
- Blanket cut chart showing what a flat percentage reduction costs.
- HTML report with light and dark themes, and machine readable JSON.
- Structured JSON logging with a per-run id.

### Fixed
- The headline figure in the report rendered a raw float, so it read as "12.0%" on one corpus and "15.63%" on the next.

## [0.1.0] - 2026-10-20

Core analysis.

### Added
- Corpus specification declaring eight rules with a stated class imbalance of roughly one true positive per 300 alerts, including one rule whose signal carries no information at all. ADR-003 covers why that rule is there.
- Reproducible labelled corpus generator, seeded, emitting only the three columns the analysis reads.
- Frontier computation: for every threshold a rule's signal offers, the volume removed and the true positives lost.
- Separation statistic, computed from ranks as the normalised Mann Whitney U.
- Stratified bootstrap percentile intervals on every published statistic, with true positives resampled within their own class. ADR-001 covers why the stratification is a requirement rather than a refinement.
- Stream level rollup: free volume, analyst hours, and the cost of a blanket cut.

### Fixed
- `_first_loss` read the wrong end of the zero loss run, so removable volume was exactly 0.0 for every rule. The value was plausible enough to be rationalised rather than noticed, and what found it was a ten alert example worked out on paper first.

[Unreleased]: https://github.com/__GITHUB_USERNAME__/alert-triage-economics/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/__GITHUB_USERNAME__/alert-triage-economics/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/__GITHUB_USERNAME__/alert-triage-economics/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/__GITHUB_USERNAME__/alert-triage-economics/releases/tag/v0.1.0
