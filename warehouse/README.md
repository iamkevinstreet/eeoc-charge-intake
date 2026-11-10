# EEOC charge warehouse

[![ci](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml/badge.svg)](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml)
[![codeql](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/codeql.yml/badge.svg)](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/codeql.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../LICENSE)

Every reviewed charge as facts, bridges and dimensions, beside the EEOC's national charge statistics: dlt loads the review exports and the EEOC's tables, dbt models them, and Airflow schedules both. For legal businesses.

These are the repository's data layers, in a folder of their own beside the review app. Run every
command below from this folder.

## In the blueprint

Every project follows the same seven layers, and fills only the ones its problem needs.

| Layer | Here |
| --- | --- |
| Sources | The review service's exports under contract v1, and the EEOC's Table E1a, charge receipts by basis, FY 1997 to FY 2025 |
| Ingestion | dlt: every export checked against the contract before a row is made, merged on its key; the table read by its shape, its hash on every row |
| Storage | `raw_reviews` and `raw_eeoc_stats` in one DuckDB file on a laptop and in CI; Databricks or Snowflake in production |
| Modeling | Staging and intermediate views, then the `charges` mart (facts, bridges and dimensions, the respondent type 2) and the `national` mart, every table under a contract |
| Serving | The marts, and the dbt docs site with its lineage graph |
| Intelligence | Upstream, in the app: the extraction. The warehouse counts what reviewers had to correct |
| Product | Not yet: the case study's figures and a dashboard will read the marts |

## Status

| | |
| --- | --- |
| Works today | Both loads and the build on DuckDB: 4 staging and 4 intermediate views, 15 tables, 2 seeds, 4 unit tests and the data tests, the EEOC's published totals among them. 29 offline tests |
| The data | The five live runs' 360 documents replayed as reviewed exports (below), and Table E1a, which CI reads from the EEOC's site |
| Every day | The `daily` workflow runs each DAG end to end through Airflow on DuckDB, keeps the warehouse and its docs as an artifact and copies them to the lake, and loads and builds on Databricks, on [data-platform-aws-databricks](https://github.com/iamkevinstreet/data-platform-aws-databricks), and on Snowflake, on [data-platform-aws-snowflake](https://github.com/iamkevinstreet/data-platform-aws-snowflake), once that platform is applied |
| Access on Databricks | A column mask on the raw values shows the charging party's name to no one, the build included, and the platform grants loading, building and reading to three groups. The daily build's test that it reads no name passes there |
| Access on Snowflake | Written, not yet run: the load and the build each sign in as a service user of their own with the job's OIDC token, so no key is stored, and a masking policy shows the name to no role in use. Waits on the platform's snowflake root being applied |
| Next | The review service's own exports folder as a source |

## Where the reviews come from

No person reviewed these charges. `make reviews`, from the repository's root, replays every document
of the five committed live runs as the review service would export it: a reviewer who knows each
document's true values accepts a field the model read right, rejects one it filled where the
document holds nothing, and edits any other to the true value; the summary is accepted. Every
export meets contract v1, as the service's own do. Each carries its run's start and finish as its
times, so the marts measure what had to be corrected, never how long a review took.

On those exports: 200 charges, 10 of them without a number, and 360 reviews, since 40 documents are
in all five runs. Reviewers corrected one field, 28 times: `issues`, in the first run of Oct 17,
which is the one miss the app's results show. `rpt_field_corrections` follows its share of reviews
needing a correction from 70% after that run to 7.8% after the fifth.

## Quick start

You need [uv](https://docs.astral.sh/uv/). Nothing else: no key, no account, no server.

```bash
make install   # the locked environment
make load      # the replayed exports, and Table E1a from the EEOC's site
make build     # every seed, model, contract, unit test and data test, on DuckDB
make docs      # the dbt docs site with its lineage graph, in dbt/target/static_index.html
make test      # 29 tests, offline
make check     # lint, format and strict types; the repository's root runs the code standard
```

To run the DAGs through Airflow, `make install-airflow` then `make dags-test`.

## The marts

| Model | One row per |
| --- | --- |
| `fct_charges` | Charge, as its latest review left it: number, office, dates of harm, continuing action, notice date, response due; known by its number, or by its document when the form leaves the number blank |
| `fct_reviews` | Review: its charge, and how many fields were accepted, edited, rejected or emptied by the quote check |
| `fct_field_reviews` | Review and field: the decision, whether the record ended different from what the model read |
| `bridge_charge_respondent`, `bridge_charge_basis`, `bridge_charge_issue` | Charge and each respondent it names, basis it cites, issue it raises |
| `dim_respondent` | Respondent per spelling of its name, type 2, valid from the export that first recorded it |
| `dim_charging_party` | Charging party, by a key and an initial only |
| `dim_office`, `dim_basis`, `dim_issue`, `dim_date` | Office, basis (with its label in Table E1a), issue, and day with the federal fiscal year |
| `rpt_field_corrections` | Field per review, in export order: the share of its reviews so far a reviewer corrected |
| `rpt_bases_vs_national` | Basis: the share of reviewed charges citing it, beside the share of the EEOC's charges citing it in the latest fiscal year |
| `fct_receipts_by_basis` | Basis or statute per fiscal year of Table E1a: receipts, their share of all charges, the change from the year before |

## Design

- **The contract is the boundary.** The app and its warehouse share a repository, and the export
  contract is what one promises the other: the loader refuses an export that breaks it, naming its
  file and line, before any row is written.
- **History where something changes.** A respondent carries only its name, so its type 2 history is
  the spelling recorded: a version begins when a later export records the same respondent, by its
  name in lower case and trimmed, spelled another way. The replayed exports hold one spelling each;
  a unit test shows the change.
- **No name in a mart, and on Databricks or Snowflake in no query.** The marts hold a key and an
  initial, and `fct_field_reviews` shows no value for a field that names a person. On Databricks
  and Snowflake, every load ends by putting a mask on the raw values
  ([`pipelines/masks.py`](pipelines/masks.py)): a value of a field in `[reviews] personal_fields`
  shows as its initial and a fingerprint of its text, such as `J. 3f9a0c2b71de`, to everyone outside
  `personal-data-readers`, a Databricks account group left empty, or without
  `PERSONAL_DATA_READER`, a Snowflake role granted to no one. Databricks calls it a column mask,
  Snowflake a masking policy, and both compute the same fingerprint. The mask binds the table's
  owner too, and the build: the fingerprint tells two people apart and the initial is all the marts
  keep, so dbt reads nothing more, and a test fails the build if it ever reads a name. The fingerprint is an unsalted hash, so it stops reading, not guessing: someone
  who already suspects a name can hash it and compare. The platform's grants keep readers out of the
  raw and staging schemas altogether. DuckDB has no masks; there the build reads the name, and the
  marts still hold only the key and the initial.
- **The published totals are a test.** The build fails unless Table E1a's total charges equal the
  EEOC's own reports for FY 2023 to 2025: 81,055, 88,531 and 88,201, in
  [`dbt/seeds/published_totals.csv`](dbt/seeds/published_totals.csv) with each report's page.
- **The generator is not a sample.** `rpt_bases_vs_national` sets the generated charges' mix of
  bases beside the nation's to show how far the test documents are from real ones, not to estimate
  anything.

## Configuration

Every setting is in [`config/config.toml`](config/config.toml), at its default, and a test keeps it
equal to the defaults in code. A load to DuckDB needs no secret. See
[`config/README.md`](config/README.md).

## Testing

`make test` runs 29 tests with no network: the table read by its shape, on workbooks the tests lay
out as the EEOC does; every committed export against the contract, a refused one, and a load done
twice; the whole build on the committed exports and a stand-in table with the published totals; the
masks' statements, run against stand-ins for Databricks and Snowflake; the settings, the command,
and the DAGs as Airflow parses them. CI also loads the real table from the EEOC's site and builds on
it.

## Project layout

| Path | What it holds |
| --- | --- |
| `pipelines/` | The two dlt sources, the raw contract, and `python -m pipelines`, which the Makefile, CI and the DAGs run |
| `dbt/` | The dbt project: staging, intermediate and the two marts, seeds, macros and tests ([`dbt/README.md`](dbt/README.md)) |
| `dags/` | The Airflow 3 DAGs ([`dags/README.md`](dags/README.md)) |
| `config/` | Every setting and the secrets template ([`config/README.md`](config/README.md)) |
| `tests/` | The tests, offline |
| `data/` | Only `generated/`, ignored: the warehouse, dlt's state, Airflow's home ([`data/README.md`](data/README.md)) |

The exports it loads are the repository's [`data/reviews/`](../data/reviews/), and the contract they
meet is the app's,
[`review_export_v1.json`](../backend/src/eeoc_intake/contracts/review_export_v1.json).

## Changelog and license

[CHANGELOG.md](../CHANGELOG.md). Apache 2.0: see [LICENSE](../LICENSE) and
[NOTICE](../NOTICE). Security reports: [SECURITY.md](../SECURITY.md).
