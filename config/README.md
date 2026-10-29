# config

[`settings.toml`](settings.toml) lists every setting the service, the evaluation and the dashboard
read, at its default. It holds no secrets: those go in `.env` (copy
[`.env.example`](../.env.example)), and the service refuses to start if a secret is written here.

## How a value is chosen

Highest first: an environment variable, then `.env`, then this file, then the default in
[`backend/src/eeoc_intake/config.py`](../backend/src/eeoc_intake/config.py). Each key's
environment name is its section and key joined by an underscore, in capitals: `[samples] count` is
`SAMPLES_COUNT`.
`SETTINGS_FILE` points the service at a different file. Every setting is logged at startup, secrets
masked, in the `service.start` event.

A test (`backend/tests/test_config.py`) keeps this file equal to the defaults in code, so the two
cannot drift. The service and the dashboard have no sign-in, so a host other than this machine's
stops either one at startup.

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
