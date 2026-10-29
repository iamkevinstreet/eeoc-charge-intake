# config

[`config.toml`](config.toml) lists every setting the service, the evaluation, the dashboard and the
review screen read, at its default, and every value two parts of the code share. It holds no
secrets: those go in `config/.env` (copy [`.env.example`](.env.example), which names each one), and
the service refuses to start if a secret is written in `config.toml`.

## How a value is chosen

Highest first: an environment variable, then `config/.env`, then `config.toml`, then the default in
[`backend/src/eeoc_intake/config.py`](../backend/src/eeoc_intake/config.py). Each key's
environment name is its section and key joined by an underscore, in capitals: `[samples] count` is
`SAMPLES_COUNT`. A nested table is one setting: `[labels.fields]` is `labels_fields`.
`SETTINGS_FILE` points the service at a different file. Every setting is logged at startup, secrets
masked, in the `service.start` event.

A test (`backend/tests/test_config.py`) keeps `config.toml` equal to the defaults in code, so the two
cannot drift. The service and the dashboard have no sign-in, so a host other than this machine's
stops either one at startup.

The review screen reads the few keys it needs from `config.toml` when it is built (the list is in
[`frontend/vite.config.ts`](../frontend/vite.config.ts)), never anything from `config/.env`. An
environment variable changes the backend only; rebuild the review screen after changing a key it
reads.

## Every setting

| Setting | Default | What it does |
| --- | --- | --- |
| `[llm] provider` | `fake` | `anthropic`, `openai`, `azure`, or `fake`: demo mode, the offline stand-in |
| `[llm] model` | `claude-sonnet-5-5` | The model that reads the documents |
| `[llm] judge_model` | `claude-sonnet-5-5` | Unused here: fields are scored by exact match |
| `[llm] embedding_model` | `text-embedding-3-small` | Unused here |
| `[llm] max_tokens` | `2048` | The most tokens one extraction may write |
| `[llm] temperature` | `0.0` | 0 keeps runs repeatable |
| `[llm] max_retries` | `3` | Retries for model failures that can succeed later |
| `[llm] timeout_s` | `60.0` | How long one model call may take |
| `[azure_openai] endpoint` | unset | The Azure OpenAI resource; only for the `azure` provider |
| `[azure_openai] api_version` | `2024-10-21` | Only for the `azure` provider |
| `[eval] budget_usd` | `5.0` | A process stops calling the model once it has spent this |
| `[log] dir` | `logs` | Where the daily JSON log files go |
| `[log] level` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `[log] redact` | `true` | Removes emails, phone numbers and ID-like numbers from log lines |
| `[log] trace` | `false` | Prints the logger lines (once switched on) as HH:MM:SS traces |
| `[data] samples` | `data/generated` | The generated charges and notices, and `cases.jsonl` |
| `[data] results` | `data/evals/results` | Live evaluation results, committed |
| `[data] smoke` | `data/evals/smoke` | Offline smoke results, never committed |
| `[data] extractions` | `data/extractions` | Whole extractions a live run saves for the case study |
| `[data] export` | `data/export` | The CSV files for Tableau |
| `[data] figures` | `figures.json` | The case study's figures, written into the results folder |
| `[samples] count` | `30` | How many documents to generate |
| `[samples] seed` | `2026` | The seed; the same seed always makes the same documents |
| `[samples] hard_every` | `5` | Every fifth document is a hard case |
| `[extract] response_days` | `30` | A position statement is due this many days after the notice |
| `[extract] dump` | `8` | How many whole extractions a live run saves |
| `[api] host` | `127.0.0.1` | The address the service listens on: this machine only |
| `[api] port` | `8000` | The port |
| `[api] extracts_per_minute` | `6` | Per client; each extraction with a real model costs money |
| `[api] max_upload_bytes` | `10000000` | The largest PDF an upload may be |
| `[api] max_reviews` | `200` | The most reviews kept in memory; the oldest go first |
| `[api] allowed_origins` | `http://localhost:5173` | Browser origins allowed to call the API |
| `[api] allowed_hosts` | `localhost`, `127.0.0.1` | Host names requests may be addressed to |
| `[dashboard] host` | `127.0.0.1` | The address the dashboard listens on: this machine only |
| `[dashboard] port` | `8050` | The dashboard's port |
| `[ui] dist` | `frontend/dist` | The built review screen the service serves at `/` |

## Values the code shares

These tables tune nothing. Each names something two parts of the code must agree on, so it is
written once, here, with a comment on every key in `config.toml`. Change one only together with
whatever else depends on it: a column name, say, changes the Tableau CSV files too.

| Table | What it holds | Read by |
| --- | --- | --- |
| `[api] prefix`, `[api] request_id_header` | The routes' prefix, `/api/v1`, and the header that carries a request's id | The service and the review screen |
| `[demo] provider` | The provider that means demo mode, `fake` | The service, the evaluation and the review screen |
| `[record]` | The fields the code names one by one: the notice date, the summary, the yes or no field, the list fields | The extraction, the reviews and the review screen |
| `[scores]` | The names of the scores a document gets, and the prefix of each field's own score | The scoring, the dashboard and the review screen |
| `[labels]`, `[labels.fields]`, `[labels.kinds]` | The words people read: yes and no, what joins a list, each field's and each kind of document's name | The dashboard and the review screen |
| `[units]`, `[files] encoding` | Milliseconds in a second, percent in a whole, and the encoding of every file read or written | The backend; the review screen reads `[units]` too |
| `[eval] results_key`, `[samples] cases`, `clean`, `charge_input`, `notice_input` | How a run file and a case are written and read | The generator, the evaluation, the service and the dashboard |
| `[stats]` | The two tests that decide whether a change between runs is bigger than noise | The change tests and the dashboard's tiles |
| `[dashboard_ids]`, `[columns]`, `[charts]`, `[charts.kind_heads]` | The dashboard's part ids, the evaluation tables' column names, and the charts' schemes, sizes and titles | The dashboard, the case study's figures and the Tableau files |
| `[ui]` (but `dist`), `[ui.keys]` | The code link, the commands the screens suggest, two names the screens share, and the review keys | The review screen |
