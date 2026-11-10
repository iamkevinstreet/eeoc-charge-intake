# config

[`config.toml`](config.toml) lists every setting the loaders, the build and the DAGs read, at its
default. It holds no secrets: those go in `config/.env` (copy [`.env.example`](.env.example), which
names each one), and the settings refuse a secret written in `config.toml`.

## How a value is chosen

Highest first: an environment variable, then `config/.env`, then `config.toml`, then the default in
code. Each key's environment name is its section and key joined by an underscore, in capitals:
`[warehouse] path` is `WAREHOUSE_PATH`. A test (`tests/test_config.py`) keeps `config.toml` equal to
the defaults in code.

dbt reads the same warehouse: `python -m pipelines dbt ...` sets `WAREHOUSE_PATH` and the Databricks
variables from these settings before it starts dbt, and `dbt/profiles.yml` reads them.

## Every setting

| Setting | Default | What it does |
| --- | --- | --- |
| `[warehouse] destination` | `duckdb` | Where dlt loads: `duckdb`, or `databricks` with the three Databricks secrets |
| `[warehouse] path` | `data/generated/warehouse.duckdb` | The DuckDB file dlt loads and dbt builds in |
| `[warehouse] state` | `data/generated/dlt` | dlt's pipeline state |
| `[dbt] project` | `dbt` | The dbt project, which also holds `profiles.yml` |
| `[dbt] target` | `dev` | `dev` builds in DuckDB, `prod` in Databricks |
| `[dbt] threads` | `4` | Models dbt builds at once |
| `[databricks] catalog` | `kds` | The Unity Catalog catalog every schema lives in |
| `[receipts] dataset` | `raw_eeoc_stats` | The schema the EEOC's national statistics load into |
| `[receipts] url`, `timeout_s` | Table E1a of April 2026, `60.0` | Where the EEOC publishes the table, and how long its download may take |
| `[reviews] dataset` | `raw_reviews` | The schema the review exports load into |
| `[reviews] folder` | `../data/reviews` | The exports: one per `.json` file, as the review service writes them, or one per line of `.jsonl` |
| `[reviews] contract` | the app's `review_export_v1.json` | The JSON Schema every export must meet before it loads |
| `[reviews] personal_fields` | `["charging_party"]` | The fields whose values name a person: never in a mart, masked in the raw table on Databricks. dbt's `personal_fields` variable must match, and a test checks it does |
| `[reviews] personal_readers` | `personal-data-readers` | The account group the mask shows a name to, made in the workspace and left empty, so no query returns a name |
| `[files] encoding` | `utf-8` | Every file read or written |
| `[log] dir`, `level` | `logs`, `INFO` | Where `kds.logs` writes one JSON line per event, and from what level |

The secrets, in `config/.env` or the environment only: `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`
and `DATABRICKS_TOKEN`.
