# Changelog

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
