# Changelog

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
