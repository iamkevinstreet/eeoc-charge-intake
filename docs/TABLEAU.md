# Evaluation results in Tableau

The export writes three tidy CSV files that Tableau reads directly. They come from the same frames as the
Dash dashboard, so both show the same numbers.

```
python -m eeoc_intake.evals.export
# eeoc_intake/evals/results/export/runs.csv       one row per evaluation run
# eeoc_intake/evals/results/export/documents.csv  one row per document in a run
# eeoc_intake/evals/results/export/fields.csv     one row per (document, field): correct 0/1, returned, expected
```

The live workflow writes the same three files for the live runs to `eeoc_intake/evals/results/live/export/`, so
the current ones can be downloaded from the repository without running anything.

## Connect

1. Tableau Desktop or Tableau Public: Connect, Text file, pick `fields.csv`.
2. Drag `documents.csv` next to it and relate on `run_id` and `case_id`. Add `runs.csv` related on `run_id`.
   Relationships (not joins) keep the per-field rows from multiplying the per-document measures.

## Sheets worth building

| Sheet | Rows | Columns | Marks | Note |
| --- | --- | --- | --- | --- |
| Accuracy by field | `field` | `AVG(correct)` | bar | Sort descending; label the bar ends; one colour. |
| Field by case kind | `field` | `case_kind` | square, colour `AVG(correct)` | Sequential single-hue colour, 0 to 1. Add `COUNTD(case_id)` to the column header. |
| Runs over time | `started_at` (exact date) | `AVG(field_accuracy)` from documents | line, colour `model` | One line per model, label the last point. |
| Time per document | `run` | `latency_ms` / 1000 | box plot | Each dot is a document; hover shows `case_id`. |
| Cost per document | `run` | `AVG(cost_usd)` | bar | List prices as of the run; see `prices_as_of` in the results JSON. |
| What went wrong | `run`, `case_id`, `field` | `returned`, `expected`, `removed_by_verification` | text | Filter `correct = 0`. The reviewer's view of failures. |

A dashboard with the accuracy bar, the field by case kind grid and the failure table reads well on one screen;
put the run filter (`run`) at the top and apply it to all sheets.

## Style

The published dashboard follows the design of kevindstreet.com and of the Dash app, so it sits in the case
study without looking pasted in. Tableau Public draws with its own fonts; Tableau Book for text and Tableau
Medium for titles are the closest to Geist. Publish a light and a dark version; the case study can then show
the one that matches the visitor's setting.

| Part | Light | Dark |
| --- | --- | --- |
| Dashboard and sheet background | `#ffffff` | `#121419` |
| Outer padding and gaps | `#f5f5f2` | `#0a0b0e` |
| Text | `#111214` | `#f2f3f5` |
| Labels, axis text | `#585d66` | `#9aa1ac` |
| Gridlines, dividers | `#ecece8`, 1 px, solid | `#1a1d24`, 1 px, solid |
| Run in focus | `#111214` | `#f2f3f5` |
| Earlier run | `#80868f` | `#7d8490` |
| Row that changed (reference band) | `#ffe45c` at 45% | `#f3cf4a` at 15% |
| Field by kind grid, 0% to 100% | `#ecece8` to `#13794a` | `#1a1d24` to `#5dd39e` |

- Accuracy by field as dots, one per run, joined by a line where the runs differ; label only those values.
- The field by kind grid labels only the cells below 100%; the colour carries the rest.
- Titles in sentence case and the same words as the Dash app; no workbook title bar, no toolbar, no
  borders around sheets.
- The run filter at the top, applied to every sheet.

## Publishing

Tableau Public workbooks are public by definition, and only Tableau Public vizzes can be embedded on a public
page without a sign-in. The generated documents contain no real names or facts, so the export is safe to
publish there. Tableau Cloud needs every viewer to sign in, which suits a client's own site but not a
portfolio page. Live runs on real documents would not belong on Tableau Public; keep those in Tableau Cloud
or Desktop.

Web authoring on Tableau Public: sign in at public.tableau.com, choose Create, then Web Authoring, upload
`fields.csv`, and build the sheets above. Publish, open the viz, and use Share to get the embed code.
