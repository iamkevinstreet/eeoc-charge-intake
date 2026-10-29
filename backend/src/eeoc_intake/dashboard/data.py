########################################################################
#              backend/src/eeoc_intake/dashboard/data.py               #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Reads the live and smoke run files into the      #
#                     tables the dashboard and the export share.       #
########################################################################
"""Run files in, three tidy tables out, for the dashboard and export.

Every run file (a JSON object with a "results" key) in the live folder,
and in the smoke folder when one is given, is one run; index.json and
figures.json sit beside the runs and are skipped. The dashboard and
the Tableau export (evals/export.py) read the same tables, so they
always agree. A table's columns are the keyword names its rows are
built with; the constants below name the ones other modules read.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd
from kds.logs import get_logger

from eeoc_intake.core.schema import SCORED_FIELDS
from eeoc_intake.dashboard.theme import FIELD_LABELS, KIND_LABELS, MAX_RUNS

# Module constants
log = get_logger(__name__)
# log.debug("Names the kind of run that called a real model")
LIVE: Final = "live"
# log.debug("Names the kind of run that answered from the known answers")
SMOKE: Final = "smoke"
# log.debug("Names the key that only a run file has")
RESULTS: Final = "results"
# log.debug("Names the key that holds a document's scores")
SCORES: Final = "scores"
# log.debug("Names the run id column")
RUN_ID: Final = "run_id"
# log.debug("Names the column of each run's long label")
RUN: Final = "run"
# log.debug("Names the model column")
MODEL: Final = "model"
# log.debug("Names the start time column")
STARTED_AT: Final = "started_at"
# log.debug("Names the column that says whether a run is live or smoke")
KIND: Final = "kind"
# log.debug("Names the document id column")
CASE_ID: Final = "case_id"
# log.debug("Names the kind of document column")
CASE_KIND: Final = "case_kind"
# log.debug("Names the column of each document's time, in milliseconds")
LATENCY_MS: Final = "latency_ms"
# log.debug("Names the runs table's cost per document column")
COST_PER_CASE: Final = "cost_per_case_usd"
# log.debug("Names the field column")
FIELD: Final = "field"
# log.debug("Names the column that is 1 when a field is right and 0 when not")
CORRECT: Final = "correct"
# log.debug("Names the column of the value the model returned, as JSON")
VALUE: Final = "value"
# log.debug("Names the column of the known answer, as JSON")
EXPECTED: Final = "expected"
# log.debug("Names the column that says verification removed the value")
REMOVED: Final = "removed_by_verification"
# log.debug("Lists the summary measures a run's row carries, in column order")
SUMMARY_COLUMNS: Final = (
    "field_accuracy",
    "unsupported_rate",
    "false_abstentions",
    "guesses",
    "latency_p50_ms",
    "latency_p95_ms",
    COST_PER_CASE,
    "cost_total_usd",
)
# log.debug("Lists the scores a document's row carries, in column order")
SCORE_COLUMNS: Final = ("field_accuracy", "unsupported_removed", "false_abstentions", "guesses")
# log.debug("Sets the kind of a document with no tag")
CLEAN: Final = "clean"
# log.debug("Sets how much of an ISO time a long label keeps: up to the minute")
TO_THE_MINUTE: Final = 16
# log.debug("Sets the word a yes is shown as")
YES: Final = "Yes"
# log.debug("Sets the word a no is shown as")
NO: Final = "No"
# log.debug("Sets the encoding run files are read in")
ENCODING: Final = "utf-8"
# log.debug("Describes a table row as Dash's tables take it: values by column name")
Record = dict[str | float | int, Any]


# log.debug("Defines how the run files are read")
def load_runs(live: Path, smoke: Path | None = None) -> list[dict[str, Any]]:
    """Return every run in the folders, newest first.

    Args:
        live: The folder of live runs.
        smoke: The folder of smoke runs, when they are wanted too.

    Returns:
        Each run file's contents, with its file stem as run_id and its
        kind, live or smoke, sorted by start time. A folder that does
        not exist holds no runs.
    """
    # log.debug("Reads the live runs, then the smoke runs when a folder is given")
    runs = _read(live, LIVE) + (_read(smoke, SMOKE) if smoke is not None else [])
    # log.debug("Puts the newest first; runs that started together keep their order")
    runs.sort(key=lambda run: run[STARTED_AT], reverse=True)
    # log.debug("Returns the runs")
    return runs


# log.debug("Defines the three tidy tables")
def frames(runs: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return a row per run, per document, and per document and field.

    Args:
        runs: Runs as `load_runs` returns them.

    Returns:
        The runs, documents and fields tables, in that order.
    """
    # log.debug("Starts the run rows")
    run_rows: list[dict[str, Any]] = []
    # log.debug("Starts the document rows")
    case_rows: list[dict[str, Any]] = []
    # log.debug("Starts the field rows")
    field_rows: list[dict[str, Any]] = []
    # log.debug("Walks the runs")
    for run in runs:
        # log.debug("Labels the run with its model and start, to the minute")
        label = _long_label(run)
        # log.debug("Adds the run's row")
        run_rows.append(_run_row(run, label))
        # log.debug("Walks the run's documents")
        for case in run[RESULTS]:
            # log.debug("Takes the columns a document's row and its field rows share")
            head = _case_head(run, label, case)
            # log.debug("Adds the document's row")
            case_rows.append(_case_row(head, case))
            # log.debug("Adds a row for each field the document was scored on")
            field_rows.extend(_field_rows(head, case[SCORES]))
    # log.debug("Returns the three tables")
    return pd.DataFrame(run_rows), pd.DataFrame(case_rows), pd.DataFrame(field_rows)


# log.debug("Defines the short names of the runs picked")
def run_labels(runs_df: pd.DataFrame, run_ids: Sequence[str]) -> dict[str, str]:
    """Return a short name for each run picked: its start time in UTC.

    The model leads the name when the runs picked mix models, and a
    smoke run says so. Ids the table does not hold are left out.
    """
    # log.debug("Lists the run ids the table holds")
    known = set(runs_df[RUN_ID])
    # log.debug("Takes the rows of the runs picked, in the order picked")
    picked = runs_df.set_index(RUN_ID).loc[[r for r in run_ids if r in known]]
    # log.debug("Notes whether the runs picked mix models")
    mixed = picked[MODEL].nunique() > 1
    # log.debug("Returns each run's short name by id")
    return {str(run_id): _short_label(row, mixed=mixed) for run_id, row in picked.iterrows()}


# log.debug("Defines which of the runs asked for a table holds")
def present(frame: pd.DataFrame, run_ids: str | Sequence[str]) -> list[str]:
    """Return the runs asked for that the table holds, at most three.

    Args:
        frame: Any of the three tables.
        run_ids: One run id, or several in the order picked.

    Returns:
        The ids held, in the order asked, the first three only.
    """
    # log.debug("Treats a single id as a list of one")
    asked = [run_ids] if isinstance(run_ids, str) else list(run_ids)
    # log.debug("Lists the run ids the table holds")
    known = set(frame[RUN_ID])
    # log.debug("Returns the ids held, the first three only")
    return [r for r in asked if r in known][:MAX_RUNS]


# log.debug("Defines each run's long label, read from a table")
def long_labels(frame: pd.DataFrame, run_ids: Sequence[str]) -> dict[str, str]:
    """Return each run's long label, from its first row in the table."""
    # log.debug("Returns the run column of each run's first row")
    return {r: str(frame.loc[frame[RUN_ID] == r, RUN].iloc[0]) for r in run_ids}


# log.debug("Defines the rows of the wrong-fields table")
def wrong_rows(fields: pd.DataFrame, run_ids: Sequence[str]) -> list[Record]:
    """Return every field the runs got wrong, written as a person would.

    Args:
        fields: The fields table from `frames`.
        run_ids: The runs picked.

    Returns:
        One record per wrong field, values and Yes or No in words.
    """
    # log.debug("Keeps the wrong fields of the runs picked")
    wrong = fields[fields[RUN_ID].isin(run_ids) & (fields[CORRECT] == 0)].copy()
    # log.debug("Writes the returned and the expected values in words")
    for column in (VALUE, EXPECTED):
        # log.debug("Rewrites one column")
        wrong[column] = wrong[column].map(_readable)
    # log.debug("Writes whether verification removed the value as Yes or No")
    wrong[REMOVED] = wrong[REMOVED].map({True: YES, False: NO})
    # log.debug("Returns the rows as the table takes them")
    return records(wrong)


# log.debug("Defines a table's rows as Dash's tables take them")
def records(frame: pd.DataFrame) -> list[Record]:
    """Return each row of the table as its values by column name."""
    # log.debug("Returns the rows, keyed by column name")
    return [{str(key): value for key, value in row.items()} for row in frame.to_dict("records")]


# log.debug("Defines how one folder's run files are read")
def _read(folder: Path, kind: str) -> list[dict[str, Any]]:
    """Return a folder's runs in file-name order, marked with kind."""
    # log.debug("Starts with no runs")
    runs: list[dict[str, Any]] = []
    # log.debug("Reads each JSON file in name order")
    for path in sorted(folder.glob("*.json")):
        # log.debug("Parses the file")
        run = json.loads(path.read_text(encoding=ENCODING))
        # log.debug("Skips index.json, figures.json and anything else that is not a run")
        if RESULTS not in run:
            # log.debug("Moves to the next file")
            continue
        # log.debug("Names the run after its file")
        run[RUN_ID] = path.stem
        # log.debug("Marks the run live or smoke")
        run[KIND] = kind
        # log.debug("Keeps the run")
        runs.append(run)
    # log.debug("Returns the folder's runs")
    return runs


# log.debug("Defines a run's long label")
def _long_label(run: dict[str, Any]) -> str:
    """Return the model and start time to the minute, smoke marked."""
    # log.debug("Cuts the start time to the minute, with a space for the T")
    stamp = run[STARTED_AT][:TO_THE_MINUTE].replace("T", " ")
    # log.debug("Returns the model and time, marked when the run is a smoke run")
    return f"{run[MODEL]} {stamp}" + (" smoke" if run[KIND] == SMOKE else "")


# log.debug("Defines one run's row")
def _run_row(run: dict[str, Any], label: str) -> dict[str, Any]:
    """Return the run's row: what, when, how many, and its summary."""
    # log.debug("Reads the run's summary measures")
    summary = run["summary"]
    # log.debug("Returns the row, a measure the summary lacks as None")
    return dict(
        run_id=run[RUN_ID],
        run=label,
        model=run[MODEL],
        provider=run["provider"],
        started_at=run[STARTED_AT],
        kind=run[KIND],
        cases=run["cases"],
        failures=run["failures"],
        **{name: summary.get(name) for name in SUMMARY_COLUMNS},
    )


# log.debug("Defines the columns a document's rows share")
def _case_head(run: dict[str, Any], label: str, case: dict[str, Any]) -> dict[str, Any]:
    """Return the run's and the document's columns, with its kind."""
    # log.debug("Reads the document's tags")
    tags = case["tags"]
    # log.debug("Takes the first tag as its kind; an untagged document is clean")
    kind = tags[0] if tags else CLEAN
    # log.debug("Returns the shared columns, the kind named as the charts name it")
    return dict(
        run_id=run[RUN_ID],
        run=label,
        model=run[MODEL],
        case_id=case[CASE_ID],
        case_kind=KIND_LABELS.get(kind, kind),
    )


# log.debug("Defines one document's row")
def _case_row(head: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Return the document's row: its outcome, time, cost and scores."""
    # log.debug("Reads the document's scores")
    scores = case[SCORES]
    # log.debug("Returns the shared columns, then the document's own")
    return dict(
        head,
        ok=case["ok"],
        latency_ms=case[LATENCY_MS],
        cost_usd=case["cost_usd"],
        **{name: scores.get(name) for name in SCORE_COLUMNS},
        error=case.get("error"),
    )


# log.debug("Defines one document's field rows")
def _field_rows(head: dict[str, Any], scores: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a row per field scored: right or not, returned, expected.

    The returned and expected values are JSON text, as in the run file.
    """
    # log.debug("Reads what the model returned for each field")
    values = scores.get("values") or {}
    # log.debug("Reads the known answer for each field")
    gold = scores.get("gold") or {}
    # log.debug("Reads the fields verification removed")
    removed = scores.get("removed") or []
    # log.debug("Returns a row for each field the document was scored on, in record order")
    return [
        dict(
            head,
            field=FIELD_LABELS.get(name, name),
            correct=int(scores[f"f_{name}"]),
            value=json.dumps(values.get(name)),
            expected=json.dumps(gold.get(name)),
            removed_by_verification=name in removed,
        )
        for name in SCORED_FIELDS
        if f"f_{name}" in scores
    ]


# log.debug("Defines one run's short name")
def _short_label(row: pd.Series[Any], *, mixed: bool) -> str:
    """Return the run's start in UTC, after its model when runs mix."""
    # log.debug("Reads the start time, a trailing Z as UTC")
    when = datetime.fromisoformat(str(row[STARTED_AT]).replace("Z", "+00:00"))
    # log.debug("Writes the month, day, hours and minutes, in UTC")
    label = f"{when.strftime('%b')} {when.day}, {when.strftime('%H:%M')} UTC"
    # log.debug("Puts the model first when the runs picked mix models")
    if mixed:
        # log.debug("Adds the model")
        label = f"{row[MODEL]}, {label}"
    # log.debug("Returns the name, marked when the run is a smoke run")
    return label + (" (smoke)" if row[KIND] == SMOKE else "")


# log.debug("Defines how a value from a run file is written for a person")
def _readable(raw: str | None) -> str:
    """Return a stored value as a person would write it.

    Lists are joined with commas, booleans are Yes or No, and a missing
    value or an empty list is empty.
    """
    # log.debug("Parses the JSON text, reading nothing as None")
    value = json.loads(raw) if raw else None
    # log.debug("Writes a missing value or an empty list as empty")
    if value is None or value == []:
        # log.debug("Returns empty")
        return "empty"
    # log.debug("Joins a list with commas")
    if isinstance(value, list):
        # log.debug("Returns the joined list")
        return ", ".join(str(x) for x in value)
    # log.debug("Writes a boolean as Yes or No")
    if isinstance(value, bool):
        # log.debug("Returns Yes or No")
        return YES if value else NO
    # log.debug("Returns anything else as text")
    return str(value)
