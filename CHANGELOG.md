# Changelog

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
