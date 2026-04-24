.PHONY: env fix lint typecheck test check clean

PACKAGE := cctop
MIN_COVERAGE := 80

env:
	uv sync --group dev

fix: env
	uv run ruff check --fix

lint: env
	uv run ruff check

typecheck: env
	uv run mypy src

test: env
	uv run pytest --cov=$(PACKAGE) --cov-fail-under=$(MIN_COVERAGE) tests

check: env lint typecheck
	uv run pytest --cov=$(PACKAGE) --cov-fail-under=$(MIN_COVERAGE) tests

clean:
	rm -rf .coverage .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
