# dags

The Airflow 3 DAGs. Every task runs one command in the project's locked environment,
`uv run --no-sync python -m pipelines ...`, at the repository root, so a DAG holds no logic of its
own and the same command runs from a laptop, CI or a hosted Airflow.

| File | What it does |
| --- | --- |
| [`defaults.py`](defaults.py) | What every DAG shares: retries with backoff, a 30-minute limit, one run at a time, no backfill, the task that runs the command, and `RAW_SCHEMAS`, the raw schemas the build waits on. `.airflowignore` keeps Airflow from parsing it as a DAG |
| [`reviews.py`](reviews.py) | `load_reviews`: the review exports, each day at 05:37 UTC, updating `raw_reviews` |
| [`receipts.py`](receipts.py) | `load_receipts`: Table E1a, on the third of each month, updating `raw_eeoc_stats` |
| [`warehouse.py`](warehouse.py) | `build_warehouse`: source freshness, `dbt build`, then the docs site, whenever any raw schema changes |

Each source has a DAG that runs its load and updates an asset named for the raw schema it writes,
listed in `RAW_SCHEMAS`, so the build runs after either. Add each DAG's id to `DAGS` in the Makefile, so `make dags-test` runs it
end to end through Airflow.

`tests/test_dags.py` parses the folder with Airflow's own DagBag and checks each DAG's settings and
commands, that the build waits on every raw schema a load updates, and that `DAGS` names every DAG.
