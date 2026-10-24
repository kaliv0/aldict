.PHONY: help sync format test bench build publish clean all

help:
	@echo "Targets:"
	@echo "  sync         uv sync --all-extras --dev"
	@echo "  format       uv run ruff check && uv run ruff format"
	@echo "  test         uv run pytest"
	@echo "  bench        microbenchmarks (current vs pre-rewrite UserDict)"
	@echo "  build        uv build"
	@echo "  publish      uvx uv-publish"
	@echo "  clean        remove ruff/pytest caches"
	@echo "  all          sync format test"

sync:
	uv sync --all-extras --dev

format:
	uv run ruff check && uv run ruff format

test:
	uv run pytest

bench:
	uv run python benchmarks/bench.py

build:
	uv build

publish: build
	uvx uv-publish

clean:
	rm -rf .ruff_cache/ .pytest_cache/

all: sync format test
