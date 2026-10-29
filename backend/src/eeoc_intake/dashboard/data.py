########################################################################
#              backend/src/eeoc_intake/dashboard/data.py               #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Reads the live and smoke run files into the three tables the dashboard
and the Tableau export share, and names each run. Every run file (a
JSON object with a "results" key) in the live folder, and in the smoke
folder when one is given, is one run; index.json and figures.json sit
beside the runs and are skipped. The dashboard and the export
(evals/export.py) read the same tables, so they always agree. The
columns are named in the config's [columns] table.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Final

# Third-party
import pandas as pd
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.core.schema import SCORED_FIELDS

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the key that only a run file has, from the config")
RESULTS: Final = SETTINGS.eval_results_key
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the column of each run's long label, from the config")
RUN: Final = SETTINGS.columns_run
# log.debug("Takes the model column, from the config")
MODEL: Final = SETTINGS.columns_model
# log.debug("Takes the start time column, from the config")
STARTED_AT: Final = SETTINGS.columns_started_at
# log.debug("Takes the column that says whether a run is live or smoke, from the config")
KIND: Final = SETTINGS.columns_kind
# log.debug("Takes the document id column, from the config")
CASE_ID: Final = SETTINGS.columns_case_id
# log.debug("Takes the kind of document column, from the config")
CASE_KIND: Final = SETTINGS.columns_case_kind
# log.debug("Takes the column of each document's time, from the config")
LATENCY_MS: Final = SETTINGS.columns_latency_ms
# log.debug("Takes the runs table's cost per document column, from the config")
COST_PER_CASE: Final = SETTINGS.columns_cost_per_case
# log.debug("Takes the field column, from the config")
FIELD: Final = SETTINGS.columns_field
# log.debug("Takes the column that is 1 when a field is right, from the config")
CORRECT: Final = SETTINGS.columns_correct
# log.debug("Takes the column of the value the model returned, from the config")
VALUE: Final = SETTINGS.columns_value
# log.debug("Takes the column of the known answer, from the config")
EXPECTED: Final = SETTINGS.columns_expected
# log.debug("Takes the column that says the quote check removed the value, from the config")
REMOVED: Final = SETTINGS.columns_removed
# log.debug("Takes the kind of a document with no tag, from the config")
CLEAN: Final = SETTINGS.samples_clean
# log.debug("Takes the encoding run files are read in, from the config")
ENCODING: Final = SETTINGS.files_encoding
# log.debug("Takes the name of each field, from the config")
FIELD_LABELS: Final = SETTINGS.labels_fields
# log.debug("Takes the name of each kind of document, from the config")
KIND_LABELS: Final = SETTINGS.labels_kinds
# log.debug("Takes what comes before a field's name in its own score, from the config")
FIELD_SCORE: Final = SETTINGS.scores_field_prefix

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the kind of run that called a real model")
LIVE: Final = "live"
# log.debug("Names the kind of run that answered from the known answers")
SMOKE: Final = "smoke"
# log.debug("Names the key that holds a document's scores")
SCORES: Final = "scores"
# log.debug("Names the key and column of a run's provider")
PROVIDER: Final = "provider"
# log.debug("Names the key and column of a run's number of documents")
CASES: Final = "cases"
# log.debug("Names the key and column of a run's failed documents")
FAILURES: Final = "failures"
# log.debug("Names the key and column that say a document finished")
OK: Final = "ok"
# log.debug("Names the key and column of a document's cost")
COST_USD: Final = "cost_usd"
# log.debug("Names the key and column of a document's error")
ERROR: Final = "error"
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
# log.debug("Sets how much of an ISO time a long label keeps: up to the minute")
TO_THE_MINUTE: Final = 16


########################################################################
#                              Run tables                              #
########################################################################
# log.debug("Defines how the run files are read")
def load_runs(live: Path | None = None, smoke: Path | None = None) -> list[dict[str, Any]]:
    """Returns every run in the folders, newest first.

    Args:
        live: The folder of live runs. Required.
        smoke: The folder of smoke runs, when they are wanted too.

    Returns:
        Each run file's contents, with its file stem as run_id and its
        kind, live or smoke, sorted by start time. A folder that does
        not exist holds no runs.
    """
    # log.debug("Takes the live results folder, which the caller must give")
    live = required(live=live)
    # log.debug("Reads the live runs, then the smoke runs when a folder is given")
    runs = _read(live, LIVE) + (_read(smoke, SMOKE) if smoke is not None else [])
    # log.debug("Puts the newest first; runs that started together keep their order")
    runs.sort(key=lambda run: run[STARTED_AT], reverse=True)
    # log.debug("Returns the runs")
    return runs


# log.debug("Defines the three tidy tables")
def frames(
    runs: list[dict[str, Any]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns a row per run, per document, and per document and field.

    Args:
        runs: Runs as `load_runs` returns them. Required.

    Returns:
        The runs, documents and fields tables, in that order.
    """
    # log.debug("Takes the runs, which the caller must give")
    runs = required(runs=runs)
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
def run_labels(
    runs_df: pd.DataFrame | None = None, run_ids: Sequence[str] | None = None
) -> dict[str, str]:
    """Returns a short name for each run picked: its start time in UTC.

    The model leads the name when the runs picked mix models, and a
    smoke run says so. Ids the table does not hold are left out.

    Args:
        runs_df: The runs table from `frames`. Required.
        run_ids: The runs picked, in order. Required.

    Returns:
        Each run's short name by its id, in the order picked.
    """
    # log.debug("Takes the runs table, which the caller must give")
    runs_df = required(runs_df=runs_df)
    # log.debug("Takes the run ids, which the caller must give")
    run_ids = required(run_ids=run_ids)
    # log.debug("Lists the run ids the table holds")
    known = set(runs_df[RUN_ID])
    # log.debug("Takes the rows of the runs picked, in the order picked")
    picked = runs_df.set_index(RUN_ID).loc[[r for r in run_ids if r in known]]
    # log.debug("Notes whether the runs picked mix models")
    mixed = picked[MODEL].nunique() > 1
    # log.debug("Returns each run's short name by id")
    return {str(run_id): _short_label(row, mixed=mixed) for run_id, row in picked.iterrows()}


# log.debug("Defines how one folder's run files are read")
def _read(folder: Path | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    """Returns a folder's runs in file-name order, marked with kind.

    Args:
        folder: The folder of run files. Required.
        kind: What to mark each run as: live or smoke. Required.

    Returns:
        The folder's runs, each with its run_id and kind; none when the
        folder does not exist.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Takes the kind, which the caller must give")
    kind = required(kind=kind)
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
def _long_label(run: dict[str, Any] | None = None) -> str:
    """Returns the model and start time to the minute, smoke marked.

    Args:
        run: A run, as `_read` marks it. Required.

    Returns:
        The model and the start time to the minute, with smoke after
        it for a smoke run.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Cuts the start time to the minute, with a space for the T")
    stamp = run[STARTED_AT][:TO_THE_MINUTE].replace("T", " ")
    # log.debug("Returns the model and time, marked when the run is a smoke run")
    return f"{run[MODEL]} {stamp}" + (" smoke" if run[KIND] == SMOKE else "")


# log.debug("Defines one run's row")
def _run_row(run: dict[str, Any] | None = None, label: str | None = None) -> dict[str, Any]:
    """Returns the run's row: what, when, how many, and its summary.

    Args:
        run: A run, as `_read` marks it. Required.
        label: The run's long label. Required.

    Returns:
        The run's id, label, model, provider, start, kind, documents
        and failures, then its summary measures; a measure the summary
        lacks is None.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Reads the run's summary measures")
    summary = run["summary"]
    # log.debug("Returns the row, a measure the summary lacks as None")
    return {
        RUN_ID: run[RUN_ID],
        RUN: label,
        MODEL: run[MODEL],
        PROVIDER: run[PROVIDER],
        STARTED_AT: run[STARTED_AT],
        KIND: run[KIND],
        CASES: run[CASES],
        FAILURES: run[FAILURES],
        **{name: summary.get(name) for name in SUMMARY_COLUMNS},
    }


# log.debug("Defines the columns a document's rows share")
def _case_head(
    run: dict[str, Any] | None = None, label: str | None = None, case: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Returns the run's and the document's columns, with its kind.

    Args:
        run: The run the document is in. Required.
        label: The run's long label. Required.
        case: The document's results, from the run file. Required.

    Returns:
        The run's id, label and model, and the document's id and kind,
        the kind named as the charts name it.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Takes the label, which the caller must give")
    label = required(label=label)
    # log.debug("Takes the document, which the caller must give")
    case = required(case=case)
    # log.debug("Reads the document's tags")
    tags = case["tags"]
    # log.debug("Takes the first tag as its kind; an untagged document is clean")
    kind = tags[0] if tags else CLEAN
    # log.debug("Returns the shared columns, the kind named as the charts name it")
    return {
        RUN_ID: run[RUN_ID],
        RUN: label,
        MODEL: run[MODEL],
        CASE_ID: case[CASE_ID],
        CASE_KIND: KIND_LABELS.get(kind, kind),
    }


# log.debug("Defines one document's row")
def _case_row(
    head: dict[str, Any] | None = None, case: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Returns the document's row: its outcome, time, cost and scores.

    Args:
        head: The columns the document's rows share, from
            `_case_head`. Required.
        case: The document's results, from the run file. Required.

    Returns:
        The shared columns, then whether the document finished, its
        time, cost and scores, and any error.
    """
    # log.debug("Takes the shared columns, which the caller must give")
    head = required(head=head)
    # log.debug("Takes the document, which the caller must give")
    case = required(case=case)
    # log.debug("Reads the document's scores")
    scores = case[SCORES]
    # log.debug("Returns the shared columns, then the document's own")
    return {
        **head,
        OK: case[OK],
        LATENCY_MS: case[LATENCY_MS],
        COST_USD: case[COST_USD],
        **{name: scores.get(name) for name in SCORE_COLUMNS},
        ERROR: case.get(ERROR),
    }


# log.debug("Defines one document's field rows")
def _field_rows(
    head: dict[str, Any] | None = None, scores: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Returns a row per field scored: right or not, returned, expected.

    The returned and expected values are JSON text, as in the run file.

    Args:
        head: The columns the document's rows share, from
            `_case_head`. Required.
        scores: The document's scores, with its values and known
            answers. Required.

    Returns:
        One row per scored field, in the record's order.
    """
    # log.debug("Takes the shared columns, which the caller must give")
    head = required(head=head)
    # log.debug("Takes the scores, which the caller must give")
    scores = required(scores=scores)
    # log.debug("Reads what the model returned for each field")
    values = scores.get("values") or {}
    # log.debug("Reads the known answer for each field")
    gold = scores.get("gold") or {}
    # log.debug("Reads the fields verification removed")
    removed = scores.get("removed") or []
    # log.debug("Returns a row for each field the document was scored on, in record order")
    return [
        {
            **head,
            FIELD: FIELD_LABELS.get(name, name),
            CORRECT: int(scores[f"{FIELD_SCORE}{name}"]),
            VALUE: json.dumps(values.get(name)),
            EXPECTED: json.dumps(gold.get(name)),
            REMOVED: name in removed,
        }
        for name in SCORED_FIELDS
        if f"{FIELD_SCORE}{name}" in scores
    ]


# log.debug("Defines one run's short name")
def _short_label(row: pd.Series[Any] | None = None, *, mixed: bool | None = None) -> str:
    """Returns the run's start in UTC, after its model when runs mix.

    Args:
        row: The run's row in the runs table. Required.
        mixed: Whether the runs picked mix models. Required.

    Returns:
        The run's start in UTC, after its model when the runs mix
        models, marked when it is a smoke run.
    """
    # log.debug("Takes the row, which the caller must give")
    row = required(row=row)
    # log.debug("Takes whether the runs mix models, which the caller must give")
    mixed = required(mixed=mixed)
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
