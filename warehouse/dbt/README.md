# dbt

One dbt project, built in DuckDB (`dev`, CI) or Databricks (`prod`). Run it through
`python -m pipelines dbt <command>`, which points `profiles.yml` at the warehouse the loaders used;
`make build` and `make docs` do.

| Folder | Layer | Built as |
| --- | --- | --- |
| `models/staging/` | One view per raw table, `stg_<source>__<table>`: renamed and cast, nothing joined | Views in `staging` |
| `models/intermediate/` | Each review's latest export, its record in columns, and each charge's latest review | Views in `intermediate` |
| `models/charges/` | The reviewed charges: `fct_`, `bridge_`, `dim_` and `rpt_` tables, each with an enforced contract, in the `charges` group, public | Tables in `charges` |
| `models/national/` | The EEOC's Table E1a, with each basis's share and its change by year, in the `national` group, public | Tables in `national` |
| `seeds/` | `published_totals`, the charges the EEOC's reports say it received, and `basis_map`, each basis's label in Table E1a | Tables in `reference` |
| `macros/` | The schema names, a surrogate key both warehouses compute alike, a sorted list each adapter writes its own way, and two generic tests: a unique combination of columns, and a value between two bounds | |
| `tests/` | The published totals, one national label per basis, and the export contract's rule that an accepted field keeps what the model read and a rejected one ends empty | |

The code standard allows this folder one level more than the repository's root, as a project of its
own, so the published marts sit in a folder per domain directly under `models/`, beside the staging
and intermediate layers.

Each source's raw tables are declared in `models/staging/_<source>__sources.yml`, with a freshness
limit, so `make freshness` reports how long ago each was loaded. Every mart's YAML gives its grain
and its columns with their types, which the contract enforces; unit tests check logic on
hand-written rows. Anonymous usage reporting and the version check are off in `dbt_project.yml`.
