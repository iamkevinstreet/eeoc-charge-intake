########################################################################
#                               Makefile                               #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           One command for each routine task: install, run, #
#                     samples, check, test, eval, publish, audit.      #
########################################################################
# CI runs the same targets. Run them from the repository root, where
# config/settings.toml and data/ are found.
UV := uv run --project backend --no-sync
NPM := npm --prefix frontend
# Our own packages install from git, not PyPI, so the PyPI audit leaves them out.
KDS := kds-settings kds-logs kds-llm kds-evals kds-synthetic kds-standards kds-diagrams
AUDIT_FILE := data/generated/requirements-audit.txt

.PHONY: install run api web samples dashboard check check-backend check-frontend test \
	test-backend test-frontend eval publish audit audit-backend audit-frontend diagrams build

install:  ## The backend from uv.lock (with the dashboard) and the frontend from package-lock.json
	uv sync --project backend --locked --all-extras
	$(NPM) ci

run:  ## The API on :8000 and the review screen on :5173 together; Ctrl-C stops both
	$(MAKE) -j2 api web

api:  ## The review service alone; in demo mode it answers for the generated samples
	$(UV) python -m eeoc_intake.api

web:  ## The review screen alone; it proxies /api to :8000
	$(NPM) run dev

samples:  ## Generate the test documents and cases.jsonl into data/generated
	$(UV) python -m eeoc_intake.core.generate

dashboard:  ## The evaluation dashboard on :8050
	$(UV) python -m eeoc_intake.dashboard

check: check-backend check-frontend  ## Every linter, formatter, type check and the code standard

check-backend:
	$(UV) ruff check backend
	$(UV) ruff format --check backend
	cd backend && uv run --no-sync mypy src tests
	$(UV) kds-standards check .

check-frontend:
	$(NPM) run lint
	$(NPM) run format:check
	$(NPM) run typecheck

test: test-backend test-frontend  ## Every test, offline and deterministic

test-backend:
	cd backend && uv run --no-sync pytest -W error

test-frontend:
	$(NPM) test

eval: samples  ## The offline smoke run: the stand-in answers, whatever .env says; no key, no network
	LLM_PROVIDER=fake $(UV) python -m eeoc_intake.evals.run --name offline

publish:  ## After a live run: the figures, the Tableau CSV files and the index the case study reads
	$(UV) python -m eeoc_intake.dashboard --export-figures
	$(UV) python -m eeoc_intake.evals.export
	$(UV) python -m eeoc_intake.evals.index

audit: audit-backend audit-frontend  ## Known vulnerabilities in every locked dependency

audit-backend:
	mkdir -p data/generated
	uv export --project backend --locked --all-extras --all-groups --no-emit-project \
		$(addprefix --no-emit-package ,$(KDS)) --format requirements.txt -o $(AUDIT_FILE) --quiet
	$(UV) pip-audit --strict --require-hashes --disable-pip -r $(AUDIT_FILE)

audit-frontend:
	$(NPM) audit --audit-level=moderate

diagrams:  ## Redraw docs/architecture.svg and docs/flow.svg from docs/diagrams.toml
	$(UV) kds-diagrams docs/diagrams.toml

build:  ## The production review screen, in frontend/dist, which the service serves at /
	$(NPM) run build
