.PHONY: install ui lint test smoke run dev dashboard export clean

PY ?= .venv/bin/python

install:
	uv venv .venv && uv pip install -e ".[dev,dashboard]" && $(PY) -m pre_commit install

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

test:
	.venv/bin/pytest

smoke:
	$(PY) -m eeoc_intake.generate --n 10 --out eeoc_intake/data/generated
	$(PY) -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl --fake

ui:
	cd ui && npm ci && npm run build

run: ui
	.venv/bin/uvicorn eeoc_intake.api:app --port 8000

dev:
	.venv/bin/uvicorn eeoc_intake.api:app --reload --port 8000 & cd ui && npm run dev

dashboard:
	$(PY) -m eeoc_intake.dashboard

export:
	$(PY) -m eeoc_intake.evals.export

clean:
	rm -rf eeoc_intake/data/generated eeoc_intake/evals/results/smoke logs .pytest_cache .ruff_cache ui/dist
