"""Command line interface.

Three verbs: generate a labelled corpus, compute the frontier, and gate CI on
the cost of a proposed tuning. The gate exists so that a volume reduction target
can be checked against what it costs before anybody ships it.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import typer

from ate import __version__
from ate.config import load_config
from ate.corpus.generate import generate as generate_corpus
from ate.frontier.summary import analyse
from ate.logging import configure, get_logger
from ate.report.chart import draw_cost_curve, draw_frontier
from ate.report.render import render_html, render_json

app = typer.Typer(add_completion=False, help="Measure what an alert tuning change costs in missed detections.")
log = get_logger(__name__)

EXIT_OK = 0
EXIT_THRESHOLD_EXCEEDED = 2


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(EXIT_OK)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Print the version and exit."
    ),
    log_level: str = typer.Option("INFO", "--log-level", help="Level for the structured log on stderr."),
) -> None:
    configure(log_level.upper())


@app.command()
def generate(
    alerts: int = typer.Option(500_000, "--alerts", min=1, help="Number of alerts to generate."),
    out: Path = typer.Option(Path("data/generated/alerts.parquet"), "--out", help="Parquet file to write."),
    seed: int = typer.Option(7, "--seed", help="Seed, so a corpus is reproducible."),
) -> None:
    """Generate a synthetic labelled alert corpus."""
    result = generate_corpus(out, alerts, seed=seed)
    typer.echo(f"wrote {result.alerts:,} alerts to {result.path}")
    typer.echo(f"  true positives  {result.true_positives:,} (1 in {1 / result.overall_tp_rate:.0f})")
    for name, (count, true_positives) in sorted(result.per_rule.items(), key=lambda kv: -kv[1][0]):
        typer.echo(f"  {name:30s} {count:>9,}  tp {true_positives:>5}")


@app.command()
def frontier(
    alerts: Path = typer.Option(..., "--alerts", exists=True, help="Parquet alert corpus."),
    out: Path | None = typer.Option(None, "--out", help="Write an HTML report here."),
    json_out: Path | None = typer.Option(None, "--json", help="Write the machine readable result here."),
    charts: Path = typer.Option(Path("docs/charts"), "--charts", help="Directory for the chart PNGs."),
    resamples: int = typer.Option(0, "--resamples", min=0, help="Bootstrap resamples. 0 uses the configured default."),
) -> None:
    """Compute the tuning frontier for every rule in a corpus."""
    config = load_config()
    if resamples:
        config = replace(config, bootstrap_resamples=resamples)

    frame = pd.read_parquet(alerts)
    summary = analyse(frame, config)

    typer.echo("")
    typer.echo(f"  alerts                {summary.alerts:,}")
    typer.echo(f"  true positives        {summary.true_positives:,} (1 in {1 / summary.tp_rate:.0f})")
    typer.echo(f"  rules analysed        {summary.rules_analysed}")
    typer.echo("")
    typer.echo(f"  removable at zero loss  {summary.free_volume:,} alerts ({summary.free_volume_pct:.1f}%)")
    typer.echo(f"  analyst hours           {summary.free_hours:,.0f} at {summary.minutes_per_alert:g} min per alert")
    typer.echo(f"  rules with no signal    {len(summary.untunable)} ({summary.untunable_volume_pct:.1f}% of volume)")
    for frontier_result in summary.untunable:
        typer.echo(
            f"     {frontier_result.rule}: separation {frontier_result.separation:.3f} "
            f"[{frontier_result.separation_low:.3f}, {frontier_result.separation_high:.3f}], "
            f"{frontier_result.true_positives} true positives"
        )
    typer.echo(
        f"  too few detections      {len(summary.unmeasured)} "
        f"({summary.unmeasured_volume_pct:.1f}% of volume)"
    )
    for frontier_result in summary.unmeasured:
        typer.echo(
            f"     {frontier_result.rule}: separation {frontier_result.separation:.3f} "
            f"[{frontier_result.separation_low:.3f}, {frontier_result.separation_high:.3f}], "
            f"{frontier_result.true_positives} true positives"
        )
    typer.echo("")
    typer.echo("  cost of a blanket cut")
    for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
        typer.echo(
            f"     remove {fraction:.0%} of every rule   "
            f"lose {summary.cost_of(fraction):5.1f}% of true positives"
        )
    typer.echo("")

    chart_paths: dict[str, str] = {}
    if out:
        charts.mkdir(parents=True, exist_ok=True)
        draw_frontier(summary, charts / "frontier.png")
        draw_cost_curve(summary, charts / "blanket-cut.png")
        try:
            prefix = charts.relative_to(Path(out).parent)
        except ValueError:
            prefix = charts
        chart_paths = {
            "frontier": str(prefix / "frontier.png"),
            "blanket": str(prefix / "blanket-cut.png"),
        }
        typer.echo(f"charts       {charts}")
        typer.echo(f"html report  {render_html(summary, out, chart_paths=chart_paths)}")
    if json_out:
        typer.echo(f"json result  {render_json(summary, json_out)}")


@app.command()
def gate(
    alerts: Path = typer.Option(..., "--alerts", exists=True, help="Parquet alert corpus."),
    cut: float = typer.Option(..., "--cut", min=0.0, max=1.0, help="Proposed blanket volume reduction, as a fraction."),
    max_tp_loss_pct: float = typer.Option(5.0, "--max-tp-loss-pct", help="Fail above this true positive loss."),
    resamples: int = typer.Option(400, "--resamples", min=100, help="Bootstrap resamples."),
) -> None:
    """Exit non zero when a proposed volume cut costs too many detections."""
    config = replace(load_config(), bootstrap_resamples=resamples)
    summary = analyse(pd.read_parquet(alerts), config)
    cost = summary.cost_of(cut)

    typer.echo(f"  proposed cut          {cut:.0%} of every rule's volume")
    typer.echo(f"  true positives lost   {cost:.2f}%")
    typer.echo(f"  limit                 {max_tp_loss_pct:.2f}%")
    typer.echo(f"  untunable rules       {len(summary.untunable)}")
    typer.echo(f"  unmeasured rules      {len(summary.unmeasured)}")

    if cost > max_tp_loss_pct:
        typer.echo("")
        typer.echo(
            f"  FAIL  a {cut:.0%} cut costs {cost:.2f}% of true positives, limit is {max_tp_loss_pct:.2f}%",
            err=True,
        )
        raise typer.Exit(EXIT_THRESHOLD_EXCEEDED)

    typer.echo("")
    typer.echo("  PASS  the proposed cut is within the loss budget")


if __name__ == "__main__":  # pragma: no cover - entry point for `python -m ate.cli`
    app()
