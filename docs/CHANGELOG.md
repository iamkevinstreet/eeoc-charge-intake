# Changelog

## v0.3.1, Oct 26, 2026

- Dashboard: the design of kevindstreet.com (Geist, light and dark, one yellow highlight, green for right).
  Fields right by field is a dot plot that joins the runs and highlights the rows that changed; the field by
  kind of document grid has one panel per selected run on the same scale; the tiles show how each measure
  moved against the next selected run; the misses table shows values as written.
- `figures.json` names each trace's part in `meta.role`, so the case study can draw the figures in its own
  palette.
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
