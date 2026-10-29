# data

Everything here is made up. No charge, person or company belongs to anyone real.

| Path | What it holds | Committed |
| --- | --- | --- |
| `evals/results/` | Live evaluation results: one JSON file per run, with every document's scores, values and known answers; its Markdown table; a `-latest.md` copy per run name; `figures.json`, the case study's Plotly figures; and `index.json`, the list of files the case study fetches | Yes (generated) |
| `extractions/` | Whole extractions from live runs, the first eight of each: the record, the model's raw answer, the fields the quote check emptied, and the page text the case study's demo shows | Yes (generated) |
| `export/` | `runs.csv`, `documents.csv` and `fields.csv`, for Tableau (below) | Yes (generated) |
| `evals/smoke/` | Results of the offline smoke run, which only proves the pipeline works | No: ignored |
| `generated/` | The generated charge and notice PDFs and `cases.jsonl`, the evaluation set; also `requirements-audit.txt`, the locked list `make audit` checks | No: ignored |

## The generated documents

`make samples` writes `[samples] count` documents from `[samples] seed` into `generated/`: for each,
`charge-NNN.pdf` (an EEOC Form 5 with plain-language particulars) and `notice-NNN.pdf` (the EEOC's
notice of charge), and one line in `cases.jsonl`:

- `id`: `charge-000` and up; `tags`: the kind of document.
- `input.charge_pdf`, `input.notice_pdf`: the two files.
- `expected`: the ten scored fields' true values. `respondent` is a list for two respondents;
  `charge_number` is `null` when the form leaves it blank.

Every fifth document is a hard case, in turn: a missing charge number, a rotated first page,
particulars that run to three pages, and two respondents. The same seed always makes the same
documents; `backend/tests/test_generate.py` checks it.

## How a run is scored

Every measure is a count a reader can repeat from the results JSON
([`backend/src/eeoc_intake/evals/score.py`](../backend/src/eeoc_intake/evals/score.py)):

- **Fields right:** the final value equals the known one, case and spacing aside; a one-item list
  equals its item. The summary is never scored: it is a paraphrase.
- **Unsupported values:** fields the model filled whose quote was not on the cited page, which the
  quote check emptied.
- **Guesses:** fields filled where the document had no value. **Wrongly blank:** fields left empty
  that the document supported.
- **Time and cost:** per document, at the list prices of the date in `prices_as_of`.

The dashboard and the case study mark a change between two runs only when it is bigger than
run-to-run noise
([`backend/src/eeoc_intake/evals/stats.py`](../backend/src/eeoc_intake/evals/stats.py)): a rank
test for time, Welch's t-test for the averages per document, and Holm's correction across the six
headline numbers.

## Tableau

`make publish` (or `python -m eeoc_intake.evals.export`) writes three tidy CSV files, from the same
tables as the dashboard, so both show the same numbers:

| File | One row per | Holds |
| --- | --- | --- |
| `export/runs.csv` | evaluation run | the run's model, date, documents, prices and summary |
| `export/documents.csv` | document in a run | its kind, scores, time and cost |
| `export/fields.csv` | document and field | correct (0 or 1), the value returned, the value expected |

The live workflow writes them for every live run, so the current ones can be downloaded from the
repository without running anything.

### Connect

1. Tableau Desktop or Tableau Public: Connect, Text file, pick `fields.csv`.
2. Drag `documents.csv` next to it and relate on `run_id` and `case_id`. Add `runs.csv` related on
   `run_id`. Relationships (not joins) keep the per-field rows from multiplying the per-document
   measures.

### Sheets worth building

| Sheet | Rows | Columns | Marks | Note |
| --- | --- | --- | --- | --- |
| Accuracy by field | `field` | `AVG(correct)` | bar | Same field order as the dashboard; label only the bars below 100%; one colour. |
| Field by kind of document | `field` | `case_kind`, then `Documents of this kind` | square, colour `AVG(correct)` | Sequential single-hue colour, 0 to 1. The second column field puts the number of documents under each kind. |
| Runs over time | `started_at` (exact date) | `AVG(field_accuracy)` from documents | line, colour `model` | One line per model, label the last point. |
| Time per document | `run` | `latency_ms` / 1000 | box plot | Each dot is a document; hover shows `case_id`. |
| Cost per document | `run` | `AVG(cost_usd)` | bar | List prices as of the run; see `prices_as_of`. |
| What went wrong | `run`, `case_id`, `field` | `value` (shown as Returned), `expected`, `removed_by_verification` | text | Filter `correct = 0`: the reviewer's view of failures. |

A dashboard with the accuracy bars, the field by kind grid and the failure table reads well on one
screen; put the run filter (`run`) at the top and apply it to all sheets.

### Style

The published dashboard follows the design of kevindstreet.com and of the Dash app, so it sits in the
case study without looking pasted in. Tableau Public draws with its own fonts; Tableau Book for text
and Tableau Medium for titles are the closest to Geist.

| Part | Colour |
| --- | --- |
| Dashboard and sheet background | `#ffffff` |
| Text, and the bars for the run shown | `#111214` |
| Labels, axis text, the note under a title | `#585d66` |
| Gridlines, dividers | `#ecece8`, 1 px, solid |
| Field by kind grid, 0% to 100% | `#ecece8` to `#13794a` |

- The workbook uses the Dash app's words for the columns: Document, Kind of document, Returned,
  Expected.
- The run is a single-value dropdown at the top, applied to every sheet, with no "All" choice. The
  dashboard opens on the first run, the one with misses.
- The field by kind grid labels only the cells below 100%; the colour and its legend carry the rest.
  Each kind of document shows its number of documents under its name,
  `"(" + STR({FIXED [Run], [Kind of document] : COUNTD([Document])}) + ")"`, so a 0% over two
  documents does not read like a 0% over thirty.
- A label never rounds a share up to 100% or down to 0%, the same rule as the dashboard and the case
  study. Tableau formats a number with a fixed count of decimals, so the label is two calculated
  fields side by side, and only one of them has a value: `Label below 100%` holds whole percents
  from 10% to 99% (format `0"%"`), and `Label below 100%, decimal` holds one decimal above 99%
  (floored) and below 10% (format `0.0"%"`).
- Tooltips read "Right in 31% of 32 documents": `Share right` is the share as text under the same
  rule, and `Documents` is `COUNTD([Document])`.
- What went wrong is a list with row lines and no banding, and a note under the title that it is
  empty when every field was right.
- Titles in sentence case and the same words as the Dash app. No dashboard title (the case study's
  frame names it), no toolbar, no borders around sheets.
- Tableau Public serves one design. In dark mode the case study inverts the embed with a CSS filter
  and turns the hues back, which puts it on a near-black background with light text and lighter
  greens for higher values, close to the dark colours of the Dash app.

### Publishing

Tableau Public workbooks are public by definition, and only Tableau Public vizzes can be embedded on a
public page without a sign-in. The generated documents contain no real names or facts, so the export
is safe to publish there. Tableau Cloud needs every viewer to sign in, which suits a client's own site
but not a portfolio page. Live runs on real documents would not belong on Tableau Public; keep those
in Tableau Cloud or Desktop.

Web authoring on Tableau Public: sign in at public.tableau.com, choose Create, then Web Authoring,
upload `fields.csv`, and build the sheets above. Publish, open the viz, and use Share to get the embed
code.

### After a new live run

The published workbook holds a copy of the data, so a new run reaches it only when the data is
replaced.

1. Take `data/export/fields.csv` from the repository; it covers every live run.
2. On Tableau Public, open the workbook, choose Edit, and go to the Data Source tab. On the `fields`
   connection's menu choose Edit Connection, upload the new `fields.csv`, and choose Replace and
   Update when it asks about the file name. Create the extract again.
3. Name the new run the way the others are named: on any sheet, open the Run field's menu, choose
   Aliases, and give the new value a name such as "Third run, Oct 26, 15:39 UTC". The kinds of
   document keep their names, since their values do not change.
4. Leave the run filter on the first run and Publish. The workbook keeps its name, so the embed
   address on the case study stays the same.

### On the case study

The case study embeds the dashboard with the Tableau Embedding API (v3) and keeps it in step with the
page's run switch, which also drives the React view and the Dash app's figures.

- A `<viz-filter field="Run">` with the run's value opens the dashboard on the run the page shows, so
  it draws once.
- The page's switch calls `applyFilterAsync('Run', [alias], 'replace')` on the first worksheet. The
  API filters on what the viewer sees, so it takes the run's alias, read from
  `getDomainAsync('database')`. The filter covers the whole data source, so all three sheets follow.
- A run picked in the dashboard's own dropdown fires `filterchanged` once per sheet, carrying the
  run's value, and the page's switch moves to it. The echo of a run the page set itself is ignored.
- Until the data is replaced after a new run, the page says that run is not in the workbook yet and
  shows the latest run the workbook has.
