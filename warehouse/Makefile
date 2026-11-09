########################################################################
#                                                                      #
#                          warehouse/Makefile                          #
#                                                                      #
########################################################################
# Author:            Kevin Street
# Created on:        2026-11-09
# Last modified on:  2026-11-09
#
# One command for each routine task: install, build, docs, check, test,
# the DAGs end to end and audit, and each source's load as it is added.
# CI runs the same targets. Run them from this folder, where config/ and
# dbt/ are found.
########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
UV := uv run --no-sync
PIPELINES := $(UV) python -m pipelines
# Our own packages install from git, not PyPI, so the PyPI audit leaves them out.
KDS := kds-args kds-settings kds-logs kds-pipelines kds-standards
AUDIT_FILE := data/generated/requirements-audit.txt
# oauthlib 3.3.1, in the databricks group only: dbt-databricks 1.13.0, the newest, caps its SQL
# connector below 4.4.1, which caps oauthlib below 4. Drop these once it allows connector 4.9.
AUDIT_IGNORES := PYSEC-2026-4114 CVE-2026-49272
# Each DAG's id, in the order dags-test runs them; add one with each DAG.
DAGS := load_reviews load_receipts build_warehouse
# Airflow keeps its own database and logs under data/generated/, never in ~/airflow.
AIRFLOW_ENV := AIRFLOW_HOME=$(CURDIR)/data/generated/airflow AIRFLOW__CORE__LOAD_EXAMPLES=false \
	AIRFLOW__CORE__DAGS_FOLDER=$(CURDIR)/dags PYTHONPATH=$(CURDIR)/dags
########################################################################
#                                                                      #
#                            Routine tasks                             #
#                                                                      #
########################################################################
.PHONY: install install-airflow load load-reviews load-receipts build freshness docs check test \
	dags-test audit

install:  ## The loaders, dbt and the checks, from uv.lock
	uv sync --locked

install-airflow:  ## The same, plus Airflow, for the DAG tests and dags-test
	uv sync --locked --group airflow

load: load-reviews load-receipts  ## Both sources into the warehouse

load-reviews:  ## The review exports in [reviews] folder, each checked against contract v1
	$(PIPELINES) load reviews

load-receipts:  ## The EEOC's Table E1a, charge receipts by basis, from its site
	$(PIPELINES) load receipts

build:  ## Every seed, model, contract, unit test and data test, in dependency order
	$(PIPELINES) dbt build

freshness:  ## How long ago each raw table was loaded, against its limits
	$(PIPELINES) dbt source freshness

docs:  ## The dbt docs site, with the lineage graph, in dbt/target/
	$(PIPELINES) dbt docs generate --static

check:  ## Lint, format, strict types; the repository's root runs the code standard
	$(UV) ruff check .
	$(UV) ruff format --check .
	$(UV) mypy

test:  ## Every test, offline: fixtures, not the network; the DAG tests need install-airflow
	$(UV) pytest

dags-test:  ## Each DAG end to end through Airflow itself; needs install-airflow
	$(AIRFLOW_ENV) $(UV) airflow db migrate
	for dag in $(DAGS); do $(AIRFLOW_ENV) $(UV) airflow dags test $$dag || exit 1; done

audit:  ## Known vulnerabilities in every locked dependency, Airflow's included
	mkdir -p data/generated
	uv export --locked --all-groups --no-emit-project \
		$(addprefix --no-emit-package ,$(KDS)) --format requirements.txt -o $(AUDIT_FILE) --quiet
	$(UV) pip-audit --strict --require-hashes --disable-pip -r $(AUDIT_FILE) \
		$(addprefix --ignore-vuln ,$(AUDIT_IGNORES))
