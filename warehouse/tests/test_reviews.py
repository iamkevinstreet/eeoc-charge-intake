########################################################################
#                                                                      #
#                   warehouse/tests/test_reviews.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the review exports' loader on the committed exports, the live
runs replayed: every one meets contract v1 and becomes its three
tables' rows, an export the contract refuses fails the load naming its
file and line, and loading the same folder twice changes nothing.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

# Third-party
import duckdb
import pytest
from kds.logs import get_logger

# Local
from pipelines.config import AppSettings
from pipelines.reviews import export_id, load_reviews, read_exports, rows_of
from pipelines.rows import ExportRow, ValueRow
from support import FIELDS, committed_exports, settings_in

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the time every test's rows are stamped with")
AT: Final = datetime(2026, 11, 9, tzinfo=UTC)
# log.debug("Sets the count of one raw table, by its name")
COUNT: Final = "select count(*) from raw_reviews.{}"


########################################################################
#                                                                      #
#                         Review export tests                          #
#                                                                      #
########################################################################
# log.debug("Defines the test that every committed export meets the contract")
def test_every_committed_export_meets_the_contract() -> None:
    """The loader reads each line of each file, and refuses none."""
    # log.debug("Reads the folder the settings name")
    settings = AppSettings()
    # log.debug("Checks every export was read")
    assert len(read_exports(settings.reviews_folder, settings.reviews_contract)) == len(
        committed_exports()
    )


# log.debug("Defines the test that a refused export fails the load")
def test_an_export_the_contract_refuses_fails_naming_its_file(tmp_path: Path) -> None:
    """A decision the contract does not know stops the load.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Takes a committed export and gives one field an unknown decision")
    export = committed_exports()[0] | {"decisions": {"issues": "maybe"}}
    # log.debug("Writes it as the service writes one export")
    (tmp_path / "bad.json").write_text(json.dumps(export), encoding="utf-8")
    # log.debug("Checks the read fails, naming the file and line")
    with pytest.raises(ValueError, match=r"bad\.json:1 breaks the contract"):
        # log.debug("Reads the folder")
        read_exports(tmp_path, AppSettings().reviews_contract)


# log.debug("Defines the test of one export's rows")
def test_an_export_becomes_one_row_its_values_and_its_decisions() -> None:
    """Lists give a row per item; a yes or no is true or false."""
    # log.debug("Takes a committed export")
    export = committed_exports()[0]
    # log.debug("Makes its rows")
    tables = rows_of([("a.jsonl", export)], AT)
    # log.debug("Counts the record's items: a list's each, a single value's one")
    items = sum(
        len(v) if isinstance(v, list) else 1 for v in export["record"].values() if v is not None
    )
    # log.debug("Takes the value rows, typed")
    values = [r for r in tables["export_values"] if isinstance(r, ValueRow)]
    # log.debug("Takes the export's row, typed")
    exports = [r for r in tables["exports"] if isinstance(r, ExportRow)]
    # log.debug("Reads the record's yes or no, as text")
    action = {r.value for r in values if r.field == "continuing_action"}
    # log.debug("Checks the row counts, the key and the text of a yes or no")
    assert (
        len(exports),
        len(tables["export_decisions"]),
        sum(1 for r in values if r.version == "record"),
        exports[0].export_id,
        action <= {"true", "false"},
    ) == (1, FIELDS, items, export_id(export), True)


# log.debug("Defines the test of a real load")
def test_a_load_lands_in_duckdb_and_a_second_changes_nothing(tmp_path: Path) -> None:
    """Every export loads once; a second load merges on the keys.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds settings that keep the warehouse in the test's folder")
    settings = settings_in(tmp_path)
    # log.debug("Loads the folder twice")
    for _ in range(2):
        # log.debug("Loads it")
        load_reviews(settings)
    # log.debug("Reads the tables back")
    with duckdb.connect(str(settings.warehouse_path)) as db:
        # log.debug("Counts the exports and the decisions")
        counts = [db.execute(COUNT.format(t)).fetchone() for t in ("exports", "export_decisions")]
    # log.debug("Checks each export once, with a decision per field")
    exports = len(committed_exports())
    # log.debug("Checks the counts")
    assert counts == [(exports,), (exports * FIELDS,)]
