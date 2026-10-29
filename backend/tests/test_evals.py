########################################################################
#                     backend/tests/test_evals.py                      #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the offline evaluation end to end: scores, #
#                     results files, saved extractions and the index.  #
########################################################################
"""Tests of the evaluation run, its scores and the files it writes."""

from __future__ import annotations

import json

import pytest
from kds.evals.case import EvalCase
from kds.logs import get_logger

from eeoc_intake.config import AppSettings
from eeoc_intake.core.extract import Extraction
from eeoc_intake.core.schema import ChargeRecord, Sourced
from eeoc_intake.evals.index import build_index
from eeoc_intake.evals.run import evaluate, main
from eeoc_intake.evals.score import same, score

# Module constants
log = get_logger(__name__)


# log.debug("Defines the test: the offline run scores every field right")
def test_the_offline_run_scores_every_field_right(settings: AppSettings) -> None:
    """The stand-in answers from the known values; nothing is missed."""
    # log.debug("Runs the ten samples offline, saving two extractions")
    run = evaluate(settings, name="offline", dump=2)
    # log.debug("Checks every case ran and scored")
    assert run.cases == 10 and run.failures == 0
    # log.debug("Checks the headline score")
    assert run.summary["field_accuracy"] == 1.0
    # log.debug("Checks the results went to the smoke folder, never the live one")
    assert (settings.data_smoke / "offline-latest.md").exists()
    # log.debug("Checks nothing was written where live results go")
    assert not settings.data_results.exists()


# log.debug("Defines the test: saved extractions are listed in the index")
def test_saved_extractions_are_listed_in_the_index(settings: AppSettings) -> None:
    """The index names each saved extraction for the case study."""
    # log.debug("Runs three samples, saving two whole")
    evaluate(settings, name="offline", limit=3, dump=2)
    # log.debug("Builds the index over the smoke results and saved extractions")
    index = build_index(settings.data_smoke, settings.data_extractions)
    # log.debug("Reads the one saved folder's files")
    (files,) = index["extractions"].values()
    # log.debug("Checks two were saved and one run is listed")
    assert files == ["charge-000.json", "charge-001.json"] and len(index["runs"]) == 1
    # log.debug("Reads a saved extraction")
    saved = json.loads(
        (settings.data_extractions / next(iter(index["extractions"])) / files[0]).read_text()
    )
    # log.debug("Checks it carries the pages the demo shows")
    assert saved["case_id"] == "charge-000" and saved["pages"]["charge"]


# log.debug("Defines the test: a one item list equals its item")
def test_a_one_item_list_equals_its_item() -> None:
    """["Acme"] and "acme" are the same answer; spacing aside."""
    # log.debug("Checks the list and the item")
    assert same(["Acme Corp"], "acme  corp") and not same(["A", "B"], "A")


# log.debug("Defines the test: an emptied field counts as unsupported")
def test_an_emptied_field_counts_as_unsupported() -> None:
    """A filled field verification emptied is counted and named."""
    # log.debug("Builds a raw record with a filled office")
    raw = ChargeRecord(eeoc_office=Sourced(value="Dallas District Office"))
    # log.debug("Builds the extraction after verification emptied it")
    ex = Extraction(record=ChargeRecord(), raw=raw, removed=["eeoc_office"])
    # log.debug("Scores it against a case that has an office")
    scores = score(EvalCase(id="c", input={}, expected={"eeoc_office": "Dallas"}), ex)
    # log.debug("Checks the count, the rate and the name")
    assert scores["unsupported_removed"] == 1 and scores["unsupported_rate"] == 1.0
    # log.debug("Checks the field is listed")
    assert scores["removed"] == ["eeoc_office"]


# log.debug("Defines the test: the command writes the table and succeeds")
def test_the_command_writes_the_table_and_succeeds(
    settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """main() runs offline from settings and returns 0."""
    # log.debug("Points the command at this test's settings")
    monkeypatch.setattr("eeoc_intake.evals.run.get_app_settings", lambda: settings)
    # log.debug("Checks the command succeeds over two samples")
    assert main(["--name", "offline", "--limit", "2"]) == 0
