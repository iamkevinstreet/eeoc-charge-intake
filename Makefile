.PHONY: install lint test smoke run clean

PY ?= .venv/bin/python

install:
	uv venv .venv && uv pip install -e ".[dev]" && $(PY) -m pre_commit install

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

test:
	.venv/bin/pytest

smoke:
	$(PY) -m eeoc_intake.generate --n 10 --out eeoc_intake/data/generated
	$(PY) -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl --fake

run:
	.venv/bin/uvicorn eeoc_intake.api:app --reload

clean:
	rm -rf eeoc_intake/data/generated eeoc_intake/evals/results logs .pytest_cache .ruff_cache
