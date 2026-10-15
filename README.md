# EEOC charge intake: extraction with source spans and human review

[![ci](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml/badge.svg)](https://github.com/iamkevinstreet/eeoc-charge-intake/actions/workflows/ci.yml) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Turns a charge of discrimination (the EEOC form and its notice letter) into a structured intake record. Every
field carries the page and the exact text it came from. A field the document does not support comes back empty
with a reason. Nothing is exported until a person has accepted, edited or rejected each field.

Case study with the evaluation plan and results: https://kevindstreet.com/projects/eeoc-charge-intake-extraction/

## Layout

| Path | What it is |
| --- | --- |
| `schema.py` | `ChargeRecord`: eleven fields, each a value plus page, span, confidence and reason |
| `generate.py` | Makes the test documents: charge and notice PDFs with known answers, including hard cases |
| `extract.py` | Prompt, structured extraction through the core adapter, and span verification |
| `api.py` | FastAPI service: extract, record decisions per field, export only when every field is decided |
| `evals/run.py` | The evaluation: field accuracy, unsupported outputs, empty-field precision and recall, speed, cost |
| `ui/` | Review screen (React). Added in v0.1 |

## Run it

```sh
# 1. test documents (no API calls)
python -m eeoc_intake.generate --n 30

# 2. offline smoke evaluation: proves the pipeline without a model
python -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl --fake

# 3. real evaluation (set LLM_PROVIDER and the key in .env; the run stops at EVAL_BUDGET_USD)
python -m eeoc_intake.evals.run --cases eeoc_intake/data/generated/cases.jsonl

# 4. the service
uvicorn eeoc_intake.api:app --reload
```

## Human review point

Every field. The export endpoint returns 409 until each field has a decision.

## Data

All documents are generated. No real charge, person or company appears anywhere in this project.

## Changelog

- v0.0, Oct 13, 2026. Scaffold: schema, generator, extraction with span verification, service, evaluation.
