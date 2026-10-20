# PYTHON is the interpreter everything runs through. The console scripts that
# pip installs (pytest, ate) bind to whichever interpreter installed them, which
# is not necessarily the one on PATH: on a machine with several Pythons, a bare
# `pytest` can resolve to one that cannot import this project's dependencies.
# Running modules through an explicit interpreter removes that whole class of
# "works for me" report. Override with: make verify PYTHON=python3.12
PYTHON ?= python3

.PHONY: install verify test lint demo report bench clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests tools benchmark scripts

test:
	$(PYTHON) -m pytest --cov=ate --cov-report=term-missing --cov-report=xml

# Runs every check CI runs, in the same order, so a green local verify means a
# green build. A verify that is a subset of CI is a verify that lies.
verify: lint test
	$(PYTHON) tools/check_dependencies.py
	$(PYTHON) tools/check_contrast.py
	$(PYTHON) scripts/provenance_check.py

demo:
	$(PYTHON) -m ate.cli generate --alerts 500000 --out data/generated/alerts.parquet --seed 7
	$(PYTHON) -m ate.cli frontier --alerts data/generated/alerts.parquet \
		--out docs/report.html --json docs/frontier.json

report:
	$(PYTHON) tools/collect_metrics.py

bench:
	$(PYTHON) benchmark/run_benchmark.py

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov coverage.xml .coverage data/generated
