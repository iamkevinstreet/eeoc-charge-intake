# backend

The review service, the extraction, its evaluation and the dashboard, in Python 3.12, managed with
[uv](https://docs.astral.sh/uv/). Run every command from the repository root, where `config/` and
`data/` are.

```sh
make install          # the locked dependencies with the dashboard, hashes checked
make samples          # the generated documents, into data/generated
make api              # the service on http://127.0.0.1:8000
make dashboard        # the evaluation dashboard on http://127.0.0.1:8050
make check-backend    # ruff, mypy (strict), kds-standards
make test-backend     # every backend test, offline
make eval             # the offline smoke run over the generated documents
```

## The package

| Path | What it does |
| --- | --- |
| `eeoc_intake/config.py` | Every setting, typed and validated, read from `config/settings.toml` and `.env` |
| `core/schema.py` | The record: eleven fields, each a value with its page, quote, confidence and reason |
| `core/extract.py` | The prompt, one structured model call, and the quote check |
| `core/offline.py` | The offline stand-in, which answers from each generated document's known values |
| `core/generate.py` | The made-up charges and notices, with their answers, from a seed |
| `api/` | FastAPI under `/api/v1`: the app factory and its edge checks, the routes, the reviews, the limit |
| `evals/run.py` | The evaluation: extracts every generated document and writes the results |
| `evals/score.py` | One extraction's scores: fields right, unsupported values, guesses, wrong blanks |
| `evals/stats.py` | When a change between two runs is bigger than noise, and how a share is written |
| `evals/export.py`, `evals/index.py` | The Tableau CSV files and the index the case study reads |
| `dashboard/` | The Dash dashboard and the Plotly figures the case study draws |

Core logic never imports the web framework, so the quote check, the scoring and the generator are
tested without HTTP.

## Commands

| Command | What it does |
| --- | --- |
| `python -m eeoc_intake.api` | Serves the API, and the built review screen at `/` when `frontend/dist` exists |
| `python -m eeoc_intake.core.generate` | Writes `[samples] count` documents from `[samples] seed` |
| `python -m eeoc_intake.evals.run --name <name>` | Runs the evaluation; offline with the fake provider, live otherwise; `--dump N` saves N extractions whole |
| `python -m eeoc_intake.dashboard` | Serves the dashboard; `--export-figures` writes the case study's figures instead |
| `python -m eeoc_intake.evals.export` | Writes the three Tableau CSV files |
| `python -m eeoc_intake.evals.index` | Writes the index of committed results |

Run them as `uv run --project backend --no-sync python -m ...`, or through the Makefile.

## Conventions

- Every file carries the header box and a logger line above every statement; turn the lines on
  with `kds-standards trace on backend` and off before committing.
- Tests run in an empty temporary folder, offline, with fresh settings (`tests/conftest.py`);
  shared helpers are in `tests/support.py`.
- Our own packages (`kds-*`) install from the utils repository at one commit, pinned in
  `pyproject.toml`; nothing installs from `main`.
