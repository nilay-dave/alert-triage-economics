# Security Policy

## Supported versions

The latest minor release receives security fixes. This project is pre 1.0, so
older minors are not patched.

| Version | Supported |
| --- | --- |
| 0.3.x | yes |
| < 0.3 | no |

## Reporting a vulnerability

Open a private security advisory through the repository's Security tab rather
than a public issue. Expect an acknowledgement within three working days.

## Threat model for this tool

This runs inside a security team's own environment on data that is sensitive by
definition, so the model is worth stating plainly.

**The labelled alert corpus is the most sensitive asset a SOC holds.** It
contains not only usernames, hostnames and alert details, but the record of
which attacks were real and, by implication, which ones were missed. That is
why this repository ships a synthetic corpus and a generator rather than
anything derived from real data, and why ADR-003 treats that as a design
decision rather than a limitation.

**The tool reads three columns and nothing else.** `rule`, `signal` and
`is_true_positive`. It never reads alert payloads, usernames, hostnames or
timestamps, because the frontier is a function of the signal's distribution
within each class and nothing more. An export prepared for this tool can
therefore be three columns wide, which is a much smaller thing to protect than
an alert history. If you are preparing a real export, export only those three
columns.

**Rule names are untrusted input.** They come from somebody's SIEM and flow
into an HTML report opened in a browser, so the report template escapes
everything. `autoescape` is set unconditionally rather than through
`select_autoescape`, which decides by final file extension and would leave a
template named `report.html.j2` unescaped.

**The output is safe to attach to a ticket.** The report contains rule names,
counts and statistics. It contains no alert content.

## What this tool never does

- It never writes to the SIEM, the alert queue, or any detection content.
- It never transmits anything off the host. There are no network calls in the
  analysis path at all, which is why the test suite needs no API keys and no
  network.
- It never recommends a tuning. It reports what each candidate tuning would
  cost, and a human decides. A tool that automatically suppressed alerts on the
  strength of a bootstrap interval would be a worse idea than the problem it
  solves.

## A note on acting on the output

The `gate` verb exits non zero when a proposed cut costs more detections than a
configured budget. That budget is a policy decision, not a technical one. A
team that sets it to a number they cannot meet will disable the gate within a
week, and a team that sets it too loosely will ship detection loss through a
green build. Pick it from what the analysis reports today and ratchet it.

## Dependency hygiene

Dependabot is configured for pip and for GitHub Actions. CI runs on every pull
request and on pushes to `main`.
