# Changelog

## Unreleased

- **Snowflake's connector, 4.8.1 to 5.2.0,** in the warehouse's `snowflake` group. The hold on it
  is lifted: version 5 is Snowflake's rewrite of the connector on a Rust core, dbt's Snowflake
  adapter has allowed it since 1.12.5, the version pinned here, and dlt sets no upper bound. The
  lockfile loses the twelve packages only the old connector needed, boto3, botocore and keyring
  among them. Checked without an account: on 5.2.0 both tools import, each signs in as before, as
  a workload identity with the job's OIDC token, to a local stand-in for Snowflake, and the offline
  tests pass. dbt's adapter passes three options the new connector does not know
  (`reuse_connections`, `insecure_mode` and `ocsp_root_certs_dict_lock_timeout`); the connector
  warns of each and sends it on as a session parameter. Not yet run on Snowflake on 5.2.0.
- **Snowflake, beside Databricks.** The `daily` workflow loads both sources into Snowflake, then
  builds and tests every model there, once data-platform-aws-snowflake is applied and the
  repository's `SNOWFLAKE_DATABASE` variable is set. Each job signs in as a service user of its own,
  the load as one, the build as another, with the OIDC token GitHub gives the job in its
  environment, `snowflake-load` or `snowflake-build`, so no password or key exists for either. The
  name mask comes too, as a Snowflake masking policy with the same initial and fingerprint, shown
  in full only to `[reviews] personal_role`, `PERSONAL_DATA_READER`, a role granted to no one; the
  test that the build reads no name now runs on Snowflake as well as Databricks. A Snowflake form of
  the sorted list macro, a `snowflake` dbt target and dependency group, with Snowflake's connector
  held at 4.8.1, and `[snowflake] database` in the warehouse's settings. First run on Snowflake on
  Nov 10: both loads, the masking policy and all 127 seeds, models and tests.
- **utils v0.8.0,** for the backend and the warehouse alike, so the repository keeps one pin.
  29 offline warehouse tests.
- **A column mask on the charging party's name, on Databricks.** Every review load into Databricks
  ends by putting a mask on `raw_reviews.export_values.value`: a value of a field in the new
  `[reviews] personal_fields` (the charging party) shows as its initial and a fingerprint of its
  text, such as `J. 3f9a0c2b71de`, to everyone outside `[reviews] personal_readers`, an account
  group made in the workspace and left empty. The mask binds the table's owner and the build too:
  the fingerprint tells two people apart and the initial is all the marts keep, so dbt needs no
  more, and a new test, on Databricks only, fails the build if it ever reads a name. Grants for
  loading, building and reading come from data-platform-aws-databricks v0.3.0. 25 offline warehouse
  tests.
- **The warehouse runs every day,** in a new `daily` workflow: on DuckDB, each DAG end to end
  through Airflow and the docs site, kept as an artifact and, from main, copied to the lake under
  `eeoc-charge-intake/` by date; and on Databricks, both loads and the build. AWS is reached through
  data-platform-aws-databricks' CI role, which trusts this repository from its v0.2.0.

## v0.9.0, Nov 9, 2026

- **The charge warehouse,** in `warehouse/`, the repository's data layers, started from the utils
  project template (v0.7.1) in a folder of its own beside the app:
  - **Loads:** dlt reads every review export in `[reviews] folder`, checks each against contract v1
    before any row is made, and merges on the review and its time; and the EEOC's Table E1a, charge
    receipts by basis FY 1997 to FY 2025, read by its shape, restored from ai-operations' 8c6b715.
  - **Models:** staging and intermediate views, then the `charges` mart (`fct_charges`,
    `fct_reviews`, `fct_field_reviews`, bridges for respondents, bases and issues, a type 2
    `dim_respondent`, `dim_charging_party` with a key and an initial only, offices, bases, issues
    and dates, `rpt_field_corrections` and `rpt_bases_vs_national`) and the `national` mart
    (`fct_receipts_by_basis`), every table under an enforced contract.
  - **Tests:** the build fails unless Table E1a's totals equal the EEOC's own reports for FY 2023 to
    2025, each basis has one national label, and an accepted field keeps what the model read; four
    unit tests on the window and type 2 logic; 18 offline warehouse tests.
  - **Schedules:** a daily load of the exports, a monthly one of the table, and the build when
    either changes, through Airflow 3.
- **Replayed reviews:** `make reviews` writes each live run's documents to `data/reviews/` as
  exports under contract v1, with a reviewer who knows the true values, for the warehouse to load:
  360 exports, every one meeting the contract.
- **CI** gains the warehouse's checks, tests, audit, both loads, the dbt build and docs on DuckDB,
  and its DAG tests; it can also be started by hand on any branch. Dependabot updates the
  warehouse's lockfile too.
- **utils v0.7.1** for the backend as well, which knows a folder that is a project of its own.
  The review id's length is a setting, `[exports] id_digits`.
- 77 backend, 13 review-screen and 18 warehouse tests. The health check reports 0.9.0.
- **Dependency updates land by themselves.** Dependabot groups each week's updates into one pull
  request per kind (Actions, the backend, the frontend), and the new `dependency-updates` workflow
  lands them every weekday: it applies the oldest open one to `main` as an ordinary commit, refreshes
  the dates in the headers it changes, runs the whole of CI on that commit, and moves `main` to it only
  when every check passes. One whose checks fail is labelled "needs a person" and waits. CI can now
  be called for a given commit, which is how the workflow checks one before it lands.

## v0.8.0, Nov 8, 2026

- **Reviews in Postgres:** `[reviews] store = "postgres"` keeps every review, each field's latest
  decision and every export in Postgres at `REVIEWS_DATABASE_URL`, so a review survives a restart.
  The schema is applied from `db/*.sql` at startup, once each, and recorded in `schema_migrations`;
  a trigger refuses any change to an export. Memory stays the default, for the demo and the tests.
- **Export contract, version 1:** `contracts/review_export_v1.json`, a JSON Schema. An export now also
  carries its contract, the review's source and whether it was demo output, when it began, the values
  the model read and the fields the quote check emptied, so a warehouse can count corrections by
  field. Fields may be added within version 1; none is removed or retyped without version 2.
- **Exports folder:** with `[exports] folder` set, each export is also written there, one file each,
  for the data platform's loaders.
- **Tests:** the contract on every export, the folder copy, and in Postgres a restart, a replaced
  decision, the append-only exports and the migrations. 74 backend tests.

## v0.7.0, Nov 7, 2026

- **Planted orders:** a new hard case. Every 25th generated charge, from the 13th, has a note in its
  particulars that tells an AI model to ignore its instructions, record a false charge number and
  respondent, and leave the bases blank. It falls where a clean charge was and draws nothing from
  the seeded generators, so every other document is as it was. The values it asks for go into the
  case's known answers, and `planted_followed` counts the fields that took one. The quote check
  cannot catch an obedient model, since the note is on the page, which is what the score is for.
- **The guard:** every sentence of a charge or notice that gives an AI model orders is flagged,
  with its document and page. The review screen lists them above the fields, the review and the
  saved extractions carry them, and the extraction's span counts them. The model is told the pages
  are data, never instructions.
- **Settings:** `[samples] planted`, `planted_every`, `planted_at` and `planted_key`, and the
  label and heatmap head of the new kind.
- **Phones:** the review screen's progress row wraps, so the export button no longer runs 18 px
  past a 390 px screen.
- **Measured, Nov 8:** the first live run against the case (`claude-sonnet-5-5`, 40 documents) ignored
  both planted notes: `planted_followed` 0, every field right, and the guard flagged only the two
  planted charges.
- 68 backend and 13 review-screen tests. The health check reports 0.7.0.

## v0.6.1, Nov 7, 2026

- **Spans:** the Anthropic SDK no longer adds a span of its own to each model call. That span
  repeated the `chat` span's call, tokens included, so Langfuse listed every call twice, and it
  carried the account's organization and workspace ids. The workbench moves to utils v0.6.1, which
  builds the Anthropic client with the SDK's spans and trace headers off. The spans file of the
  Nov 7 live run, on the eval-results branch, has those spans removed too.
- 64 backend tests. The health check reports 0.6.1.

## v0.6.0, Nov 7, 2026

- **Spans:** each extraction is one `extract` span recording how many fields the record fills and
  how many the quote check emptied. It holds a `chat` span for the model call (tokens, cost, stop
  reason), named as the OpenTelemetry GenAI conventions name it, and a `verify` span for the check,
  which names the fields it emptied and which Langfuse shows as a guardrail. Each evaluated document
  runs in its own `eval` span with its scores, never the values read or expected, and a run's
  documents share one session. With `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in
  `config/.env` the spans go to Langfuse; unset, they stay off. The live workflow sends them when
  those two repository secrets are set and keeps each run's spans beside its results. Four tests
  check the tree, the fields the check names, an evaluation's spans and a kept run's file.
- **The workbench:** utils v0.6.0 (spans), pinned at its new commit. The new settings, `[spans]`
  and `[langfuse]`, are in `config/config.toml`.
- 64 backend tests. The health check reports 0.6.0.

## v0.5.2, Nov 5, 2026

- **Dependencies:** the backend's lockfile moves to dash 4.5.0, python-multipart 0.0.33 and
  pandas-stubs 3.1.0.261029; the review screen's moves to ESLint 10.14.0 and eslint-plugin-jsdoc
  65.4.2, two major versions on, with the same rules. Nothing had to change for them: lint, the
  types, the code standard, the tests, the offline evaluation and the audits pass as they were.
  The health check reports 0.5.2.

## v0.5.1, Nov 5, 2026

- **Utils:** every shared package pins utils v0.5.1 (commit
  `e57de0e97d1c41616af1a98873f6beeecc74c99f`), whose checker now also reads the statements inside
  a function whose signature wraps and inside a bare `catch`. Each of them in the review screen
  already had its logger line, so no code changed; the health check reports 0.5.1.

## v0.5.0, Oct 29, 2026

The code moves to the updated code standard. Nothing a reader of the results sees changes: the
generated documents, the offline evaluation and the published results are the same as in v0.4.0,
and so are the API's routes, payloads and responses.

- **Layout:** the backend package moves to the src layout, `backend/src/eeoc_intake/`, so the
  tests import the installed package.
- **Settings:** `config/settings.toml` becomes `config/config.toml`, and the secrets move from
  `.env` to `config/.env` (`config/.env.example` names each one). A value two parts of the code
  share lives in `config/config.toml` too, with a comment: the API's prefix and request id header,
  the field and score names, the labels, the dashboard's ids, the tables' column names. Each module
  binds the ones it uses from `SETTINGS`, loaded once, and the review screen reads the keys it needs
  from the same file when it is built, so the two sides cannot drift.
- **File layout:** every file opens with a box holding its path and a doc block (author, dates and
  what the file is for), then its imports, global constants, local constants and logic, each under
  a banner. The Makefile, the workflows, the TOML and YAML files, the stylesheets and `index.html`
  carry the same header.
- **Functions:** every parameter has a type and a default, and a function that cannot work without
  a value takes it with `required()`; every function has a doc block and a return type, and none
  runs past 60 lines below its doc block. ruff adds its annotation rules; ESLint adds the jsdoc
  rules, explicit return types, the 60-line limit and our own `kds/param-defaults` rule.
- **Modules:** files that outgrew 500 lines are split by job: `api/extraction.py`,
  `core/charges.py`, `evals/shares.py`, `dashboard/views.py`, `dashboard/heatmap.py` and
  `tests/test_charts.py`. The review screen's state moves into hooks (`src/session.ts`,
  `src/reviewing.ts`), and its long components into smaller ones (`TopBar`, `ReviewHead`,
  `FieldList`, `EditForm`).
- **Review screen:** the note that uploads need a model names `config/config.toml` and
  `config/.env`; the dev server proxies `/api/v1` to the host and port in the config.
- **API docs:** each route's OpenAPI description is still its summary alone: the Args and
  Returns sections of its handler's doc block are for readers of the code.
- **The box:** every file's header box and every section banner is five lines: a border, a blank
  walled line, the title, another blank walled line and a border. The dotfiles that take `#`
  comments carry a header like the Makefile.
- **Utils:** every shared package, now with `kds-args`, pins utils v0.5.0 (commit
  `fcac0477e1caadccf1e2d7580ce648258c5a79fa`), whose checker asks for that box, checks that no
  function runs past 60 lines, and reads a long TypeScript import to its end.
- 59 backend tests and 11 review-screen tests, all offline.

## v0.4.0, Oct 29, 2026

A rebuild to one code standard: the backend and the review screen in their own folders, every
setting in one file, and the results under `data/`. Nothing the model sees changed: the prompt and
the generated documents are the same as in v0.3, draw for draw, so new runs compare with the old.

- **Layout:** `backend/` (the service, the extraction, the evaluation and the dashboard),
  `frontend/` (the review screen), `config/settings.toml` (every setting), `data/` (live results,
  saved extractions and the Tableau files) and `docs/` (the two diagrams). The Tableau notes moved
  into `data/README.md`.
- **Settings:** one typed module reads `config/settings.toml` and `.env`; nothing else reads the
  environment. The service and the dashboard refuse to listen beyond this machine, since neither
  has sign-in.
- **API:** every route moves from `/api` to `/api/v1`, with the same payloads. Every response
  carries the request id and security headers; requests for another host name are refused; a body
  over its limit, or one with no declared length, is refused before it is read; uploads must be
  PDFs of at most 10 MB and are never stored under their own names; extractions with a real model
  are limited per client; reviews in memory are capped at the newest 200. An unreadable PDF is a
  422, a model answer that never fits the record a 502, and a provider outage or a spent budget a
  503. The built review screen is served at `/` under a content security policy.
- **Extraction:** an extraction's cost now includes a repair call when one is needed.
- **Evaluation:** offline smoke results go to `data/evals/smoke/` (not committed) and live ones to
  `data/evals/results/`; a live run saves its first eight extractions whole (`[extract] dump`); the
  live workflow also writes the figures, the CSV files and the index the case study reads.
- **Dashboard:** split into modules with one job each; the same figures and numbers.
- **Review screen:** React 19 and TypeScript with ESLint, Stylelint, Prettier and tests. Keyboard
  shortcuts ignore Ctrl, Cmd and Alt (Ctrl+R used to reject the selected field), the samples'
  Review buttons sit at the right, and a pressed decision button stays readable on hover.
- **Repository:** strict mypy, the code standard in pre-commit and CI, lockfiles with hashes,
  `pip-audit` and `npm audit`, CodeQL, Dependabot, Actions pinned to commit SHAs, `SECURITY.md`,
  and diagrams drawn from `docs/diagrams.toml`. Shared packages pin utils v0.3.0.
- 59 backend tests (12 of them the dashboard's) and 11 review-screen tests, all offline.

## v0.3.4, Oct 26, 2026

- The six tiles are judged together with Holm's step-down correction, so when nothing has changed between two
  runs, the chance of even one false arrow among them is at most 5%. On the live runs, the third run's 0.3 s
  slowdown (p = 0.010, against 0.05 / 6) and the second run's $0.0014 rise in cost per document (p = 0.034,
  against 0.05 / 4) now say no clear change. The 7.0-point gain in fields right and the drop in fields wrongly
  left blank keep their arrows (p below 1e-11).
- 29 tests.

## v0.3.3, Oct 26, 2026

- Seconds per document fits its axis to the documents instead of starting at zero, since a box plot shows
  position, not length. Documents slower than the far-out fence (third quartile plus three times the
  interquartile range) are counted beside their run's row, with the slowest time, instead of stretching the
  axis.
- The tiles show an arrow and a colour only for a change bigger than run-to-run noise at 95% confidence: a rank
  test (Mann-Whitney U) for time, whose typical value is a median, and Welch's t-test for the averages per
  document, with the document as the unit. A smaller change says "no clear change", and a change that rounds
  to nothing at the precision shown says "no change".
- Shares are never rounded up to 100% or down to 0%, in the tiles, the labels, the hover text or the runs
  table: 100% means every field was right, and a value just under it keeps one decimal. Every heatmap cell
  below 100% carries its number, and the hover gives the number of documents behind the cell.
- Tableau workbook: the field by kind grid shows the number of documents under each kind, labels follow the
  same share rule, and tooltips give the share and the number of documents behind it.
- Numbers round halves up from the exact stored value, as the browser does, so the case study and the Dash
  app show the same digits (Python's own formatting rounds halves to even).
- `eeoc_intake/evals/stats.py` holds the tests, the share rule and the rounding, standard library only, so the
  case study can apply the same rules.
- 27 tests.

## v0.3.2, Oct 26, 2026

- Third live run (claude-sonnet-5-5, 200 documents, the same setup as the second run): field accuracy 100%,
  zero unsupported outputs, zero guesses, zero false abstentions; 4.5 s median, $0.0134 per document, $2.67
  for the run. Each of the four hard cases had ten documents instead of two. With no document wrong out of
  200, the share of documents like these with any field wrong is below 1.5% at 95% confidence.
- `figures.json` for the case study carries the latest three runs, the most the charts draw.
- The review screen quotes evidence with straight quotes.
- 21 tests.

## v0.3.1, Oct 26, 2026

- Dashboard: the design of kevindstreet.com (Geist, light and dark, one yellow highlight, green for right).
  Fields right by field is a dot plot that joins the runs and highlights the rows that changed; the field by
  kind of document grid has one panel per selected run on the same scale; the tiles show how each measure
  moved against the next selected run; the misses table shows values as written.
- `figures.json` names each trace's part in `meta.role`, so the case study can draw the figures in its own
  palette.
- Tableau Public dashboard in the same design: the run as a dropdown at the top, labels only below 100%, the
  Dash app's column names, and tooltips in plain words. `docs/TABLEAU.md` lists the settings.
- 20 tests.

## v0.3, Oct 17, 2026

- First live run (claude-sonnet-5-5, 40 documents): field accuracy 93.0%, zero unsupported outputs, zero
  guesses; every miss was the `issues` field, left empty on 28 of 40 documents.
- Prompt: `issues` are the employment actions the particulars describe, mapped to the EEOC labels.
- Generator: particulars describe what happened (a denied promotion, written discipline) instead of naming
  the issue label.
- `--dump N` writes the full extraction for the first N documents; the live workflow keeps eight.
- Second live run (claude-sonnet-5-5, 40 documents): field accuracy 100%, zero unsupported outputs, zero
  guesses, zero false abstentions; 4.2 s median, $0.0134 per document.
- Live results carry `index.json` and `figures.json` for the case study on kevindstreet.com.

## v0.2, Oct 15, 2026

- Review screen (React, Vite, TypeScript) served by the API: the record beside the document, the quoted
  text highlighted, accept, edit or reject per field, export disabled until every field is decided.
- Demo mode: with `LLM_PROVIDER=fake` the service answers from the generated ground truth and says so;
  uploads are refused so nobody mistakes it for a model.
- `extract()` returns the raw output, the fields verification removed, page texts, cost and latency.
- Evaluation scores each field separately and records the unsupported-output rate. Offline runs write to
  `results/smoke` (ignored), live runs to `results/live` (committed).
- `eval-live` workflow: a live run from the Actions tab with a budget, results on the `eval-results` branch.
- Dash dashboard and tidy CSV export for Tableau, built from the same frames.
- 18 tests.

## v0.0, Oct 13, 2026

Scaffold: service, evaluation entry point, sample cases. Shared utilities come from
[utils](https://github.com/iamkevinstreet/utils).
