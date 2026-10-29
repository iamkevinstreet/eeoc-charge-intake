########################################################################
#              backend/src/eeoc_intake/dashboard/views.py              #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Picks out of the run tables what the dashboard's views show: the runs
a chart can draw, each run's long label, the fields the runs got wrong
written as a person would write them, and any table's rows as Dash's
tables take them.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Final

# Third-party
import pandas as pd
from kds.args import missing, required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the run id column, from the config")
RUN_ID: Final = SETTINGS.columns_run_id
# log.debug("Takes the column of each run's long label, from the config")
RUN: Final = SETTINGS.columns_run
# log.debug("Takes the column that is 1 when a field is right, from the config")
CORRECT: Final = SETTINGS.columns_correct
# log.debug("Takes the column of the value the model returned, from the config")
VALUE: Final = SETTINGS.columns_value
# log.debug("Takes the column of the known answer, from the config")
EXPECTED: Final = SETTINGS.columns_expected
# log.debug("Takes the column that says the quote check removed the value, from the config")
REMOVED: Final = SETTINGS.columns_removed
# log.debug("Takes the word a yes is shown as, from the config")
YES: Final = SETTINGS.labels_yes
# log.debug("Takes the word a no is shown as, from the config")
NO: Final = SETTINGS.labels_no
# log.debug("Takes the most runs a chart compares, from the config")
MAX_RUNS: Final = SETTINGS.charts_max_runs

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Describes a table row as Dash's tables take it: values by column name")
Record = dict[str | float | int, Any]


########################################################################
#                           Dashboard views                            #
########################################################################
# log.debug("Defines which of the runs asked for a table holds")
def present(
    frame: pd.DataFrame | None = None, run_ids: str | Sequence[str] | None = None
) -> list[str]:
    """Returns the runs asked for that the table holds, at most three.

    Args:
        frame: Any of the three tables. Required.
        run_ids: One run id, or several in the order picked. Required.

    Returns:
        The ids held, in the order asked, the first three only.
    """
    # log.debug("Takes the table, which the caller must give")
    frame = required(frame=frame)
    # log.debug("Stops when the caller left out the run ids")
    if run_ids is None:
        # log.debug("Raises the missing-argument error")
        raise missing(run_ids=run_ids)
    # log.debug("Treats a single id as a list of one")
    asked = [run_ids] if isinstance(run_ids, str) else list(run_ids)
    # log.debug("Lists the run ids the table holds")
    known = set(frame[RUN_ID])
    # log.debug("Returns the ids held, the first three only")
    return [r for r in asked if r in known][:MAX_RUNS]


# log.debug("Defines each run's long label, read from a table")
def long_labels(
    frame: pd.DataFrame | None = None, run_ids: Sequence[str] | None = None
) -> dict[str, str]:
    """Returns each run's long label, from its first row in the table.

    Args:
        frame: Any of the three tables. Required.
        run_ids: The runs to label, each one the table holds. Required.

    Returns:
        Each run's long label by its id.
    """
    # log.debug("Takes the table, which the caller must give")
    frame = required(frame=frame)
    # log.debug("Takes the run ids, which the caller must give")
    run_ids = required(run_ids=run_ids)
    # log.debug("Returns the run column of each run's first row")
    return {r: str(frame.loc[frame[RUN_ID] == r, RUN].iloc[0]) for r in run_ids}


# log.debug("Defines the rows of the wrong-fields table")
def wrong_rows(
    fields: pd.DataFrame | None = None, run_ids: Sequence[str] | None = None
) -> list[Record]:
    """Returns each field the runs got wrong, in a person's words.

    Args:
        fields: The fields table from `frames`. Required.
        run_ids: The runs picked. Required.

    Returns:
        One record per wrong field, values and Yes or No in words.
    """
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Takes the run ids, which the caller must give")
    run_ids = required(run_ids=run_ids)
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
def records(frame: pd.DataFrame | None = None) -> list[Record]:
    """Returns each row of the table as its values by column name.

    Args:
        frame: The table. Required.

    Returns:
        Each row's values by column name, in the table's order.
    """
    # log.debug("Takes the table, which the caller must give")
    frame = required(frame=frame)
    # log.debug("Returns the rows, keyed by column name")
    return [{str(key): value for key, value in row.items()} for row in frame.to_dict("records")]


# log.debug("Defines how a value from a run file is written for a person")
def _readable(raw: str | None = None) -> str:
    """Returns a stored value as a person would write it.

    Lists are joined with commas, booleans are Yes or No, and a missing
    value or an empty list is empty.

    Args:
        raw: The value as JSON text, as the fields table holds it; None
            reads as empty.

    Returns:
        The value in words.
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
