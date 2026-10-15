# EEOC charge intake: extraction with source spans and human review

[![ci](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml/badge.svg)](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Turns a charge of discrimination (the EEOC form and its notice letter) into a structured intake record. Every
field carries the page and the exact text it came from. A field the document does not support comes back empty
with a reason. Nothing is exported until a person has accepted, edited or rejected each field.

Case study with the evaluation plan and results: https://kevindstreet.com/projects/eeoc-charge-intake-extraction/

![The review screen: the record on the left, the document on the right, the quoted text highlighted](docs/review.gif)

## How it works

1. `pypdf` reads both PDFs into per-page text.
2. One model call returns the eleven fields as JSON. Each field is a value, a page number, the exact text
   that supports it, the model's confidence, and a reason when the value is empty.
3. Span verification checks every quoted text against the cited page, ignoring case and whitespace. A field
   whose quote is not on its page is emptied before anyone sees it, and the review screen says what the model
   had claimed.
4. A reviewer accepts, edits or rejects each field. The export endpoint returns 409 until every field has a
   decision. The position-statement due date is a rule (notice date plus 30 days), never a model output.

## Layout

| Path | What it is |
| --- | --- |
| `eeoc_intake/schema.py` | `ChargeRecord`: eleven fields, each a value plus page, span, confidence and reason |
| `eeoc_intake/generate.py` | Makes the test documents: charge and notice PDFs with known answers, including hard cases |
| `eeoc_intake/extract.py` | Prompt, structured extraction through the shared adapter, and span verification |
| `eeoc_intake/fake.py` | Offline stand-in that answers from the ground truth, for the smoke run and demo mode |
| `eeoc_intake/api.py` | FastAPI service under `/api`; serves the review screen from `ui/dist` |
| `eeoc_intake/evals/run.py` | The evaluation: accuracy per field, unsupported outputs, abstentions, guesses, time, cost |
| `eeoc_intake/evals/export.py` | Tidy CSV files for Tableau (see `docs/TABLEAU.md`) |
| `eeoc_intake/dashboard.py` | Plotly Dash dashboard comparing runs |
| `eeoc_intake/tests/` | Span verification, the review service, the dashboard frames |
| `ui/` | Review screen: React, Vite, TypeScript |
| `.github/workflows/eval-live.yml` | Live evaluation against a real model, started by hand |

## Run it

```sh
make install                       # uv venv, project and dev dependencies, pre-commit
make smoke                         # generate 10 documents and run the offline evaluation (no API calls)
make test                          # 18 tests
make run                           # build the review screen and serve it at http://127.0.0.1:8000
make dashboard                     # evaluation dashboard at http://127.0.0.1:8050
make export                        # CSV files for Tableau in eeoc_intake/evals/results/export/
```

Without an API key the service runs in demo mode: it extracts the generated documents by answering from their
ground truth, and the screen says so. Set `LLM_PROVIDER` and a key in `.env` (see `.env.example`) and it
calls the model, for the generated documents and for uploads.

A live evaluation runs on GitHub: Actions, `eval-live`, Run workflow. It needs `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` as a repository secret, stops at the budget you give it, and commits the results to the
`eval-results` branch. Merge that branch to publish them under `eeoc_intake/evals/results/live/`.

## What the evaluation measures

Every generated document has known answers, so each run reports, per field and per case kind:

- field accuracy: the final value equals the ground truth
- unsupported outputs: fields the model filled whose quoted text was not on the cited page, and which
  verification removed
- false abstentions: fields left empty that the document supported
- guesses: fields filled when the document had no value
- time and cost per document at list prices, with the date the prices were taken

Case kinds: clean, missing charge number, rotated page, long particulars, two respondents. The offline smoke
run answers from the ground truth and only proves the pipeline; the numbers that matter come from live runs.

## Data

All documents are generated. No real charge, person or company appears anywhere in this project.

## Changelog

- v0.2, Oct 15, 2026. Review screen with evidence highlighting and gated export; demo mode; per-field
  scoring; live evaluation workflow; Dash dashboard and Tableau export; 18 tests.
- v0.0, Oct 13, 2026. Scaffold: schema, generator, extraction with span verification, service, evaluation.
