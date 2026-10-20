.PHONY: install verify demo report bench clean

install:
	pip install -e ".[dev]"

verify:
	ruff check src tests tools benchmark scripts
	pytest --cov=ate --cov-report=term-missing --cov-report=xml

demo:
	ate generate --alerts 500000 --out data/generated/alerts.parquet --seed 7
	ate frontier --alerts data/generated/alerts.parquet --out docs/frontier.html --json docs/frontier.json

report:
	python tools/collect_metrics.py

bench:
	python benchmark/run_benchmark.py

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov coverage.xml .coverage data/generated docs/charts
