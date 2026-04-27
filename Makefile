.PHONY: env fix lint typecheck test check run clean

PACKAGE := cctop
MIN_COVERAGE := 90

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

run: env
	uv run $(PACKAGE)

clean:
	rm -rf .venv .coverage .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
