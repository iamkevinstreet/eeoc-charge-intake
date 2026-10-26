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
| Accuracy by field | `field` | `AVG(correct)` | bar | Same field order as the Dash app; label only the bars below 100%; one colour. |
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
Medium for titles are the closest to Geist.

| Part | Colour |
| --- | --- |
| Dashboard and sheet background | `#ffffff` |
| Text, and the bars for the run shown | `#111214` |
| Labels, axis text, the note under a title | `#585d66` |
| Gridlines, dividers | `#ecece8`, 1 px, solid |
| Field by kind grid, 0% to 100% | `#ecece8` to `#13794a` |

- The workbook uses the Dash app's words for the columns: Document, Kind of document, Returned, Expected.
- The run is a single-value dropdown at the top, applied to every sheet, with no "All" choice. The
  dashboard opens on the first run, the one with misses.
- Fields right by field as bars in the Dash app's field order, labelled only where a field is below 100%.
- The field by kind grid labels only the cells below 100%; the colour and its legend carry the rest.
- What went wrong is a list with row lines and no banding, and a note under the title that it is empty
  when every field was right.
- Titles in sentence case and the same words as the Dash app. No dashboard title (the case study's frame
  names it), no toolbar, no borders around sheets. Tooltips name the field and give the share of documents
  that got it right.
- Tableau Public serves one design. In dark mode the case study inverts the embed with a CSS filter and
  turns the hues back, which puts it on a near-black background with light text and lighter greens for
  higher values, close to the dark colours of the Dash app.

## Publishing

Tableau Public workbooks are public by definition, and only Tableau Public vizzes can be embedded on a public
page without a sign-in. The generated documents contain no real names or facts, so the export is safe to
publish there. Tableau Cloud needs every viewer to sign in, which suits a client's own site but not a
portfolio page. Live runs on real documents would not belong on Tableau Public; keep those in Tableau Cloud
or Desktop.

Web authoring on Tableau Public: sign in at public.tableau.com, choose Create, then Web Authoring, upload
`fields.csv`, and build the sheets above. Publish, open the viz, and use Share to get the embed code.

## After a new live run

The published workbook holds a copy of the data, so a new run reaches it only when the data is replaced.

1. Take `eeoc_intake/evals/results/live/export/fields.csv` from the repository; it covers every live run.
2. On Tableau Public, open the workbook, choose Edit, and go to the Data Source tab. On the `fields`
   connection's menu choose Edit Connection, upload the new `fields.csv`, and choose Replace and Update when
   it asks about the file name. Create the extract again.
3. Name the new run the way the others are named: on any sheet, open the Run field's menu, choose Aliases,
   and give the new value a name such as "Third run, Oct 26, 15:39 UTC". The kinds of document keep their
   names, since their values do not change.
4. Leave the run filter on the first run and Publish. The workbook keeps its name, so the embed address on
   the case study stays the same.

## On the case study

The case study embeds the dashboard with the Tableau Embedding API (v3) and keeps it in step with the page's
run switch, which also drives the React view and the Dash app's figures.

- A `<viz-filter field="Run">` with the run's value opens the dashboard on the run the page shows, so it
  draws once.
- The page's switch calls `applyFilterAsync('Run', [alias], 'replace')` on the first worksheet. The API
  filters on what the viewer sees, so it takes the run's alias, read from `getDomainAsync('database')`. The
  filter covers the whole data source, so all three sheets follow.
- A run picked in the dashboard's own dropdown fires `filterchanged` once per sheet, carrying the run's
  value, and the page's switch moves to it. The echo of a run the page set itself is ignored.
- Until the data is replaced after a new run, the page says that run is not in the workbook yet and shows
  the latest run the workbook has.
