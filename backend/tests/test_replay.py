########################################################################
#                                                                      #
#                     backend/tests/test_replay.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the replay of live runs as reviewed exports: each field's
decision follows the known value, every export meets contract v1 and
its record follows its decisions, and each run becomes one file with
one line per document that has an extraction.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Final

# Third-party
from jsonschema import Draft202012Validator
from kds.logs import get_logger

# Local
from eeoc_intake.evals.replay import decide, replay, replay_case

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
# log.debug("Reads the export contract that ships in the package")
CONTRACT: Final = Draft202012Validator(
    json.loads(
        resources.files("eeoc_intake").joinpath("contracts/review_export_v1.json").read_text()
    ),
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)
# log.debug("Sets the true values of one made-up charge")
KNOWN: Final = {
    "charge_number": None,
    "charging_party": "Reese Underwood",
    "respondent": "Northgate Industries Corp.",
    "eeoc_office": "Atlanta District Office",
    "bases": ["Color", "Sex"],
    "issues": ["Discipline"],
    "earliest_date": "2025-12-25",
    "latest_date": "2026-07-09",
    "continuing_action": False,
    "notice_date": "2026-09-23",
}
# log.debug("Sets what the model read: a guessed number, a wrong issue, the rest right")
READ: Final = KNOWN | {
    "charge_number": "410-2026-10000",
    "issues": ["Promotion"],
    "summary": "The charging party alleges discipline because of color and sex.",
}
# log.debug("Sets a run's name and times, as its results file holds them")
RUN: Final = {
    "name": "live-claude-sonnet-5-5",
    "started_at": "2026-10-17T01:51:21+00:00",
    "finished_at": "2026-10-17T01:59:02+00:00",
}


########################################################################
#                                                                      #
#                             Replay tests                             #
#                                                                      #
########################################################################
# log.debug("Defines one document's result, as a run's file holds it")
def _case(case_id: str = "charge-004", *, ok: bool = True) -> dict[str, Any]:
    """Returns a document's result with the values above.

    Args:
        case_id: The document.
        ok: Whether the extraction succeeded.

    Returns:
        The result, its values, the known ones and no removals.
    """
    # log.debug("Returns the result")
    return {
        "case_id": case_id,
        "ok": ok,
        "scores": {"values": dict(READ), "gold": dict(KNOWN), "removed": []},
    }


# log.debug("Defines the test of each field's decision")
def test_each_decision_follows_the_known_value() -> None:
    """Right is accepted, a guess rejected, a wrong value edited."""
    # log.debug("Checks the four kinds of field")
    assert [
        decide("respondent", ["Northgate Industries Corp."], "Northgate Industries Corp."),
        decide("charge_number", "410-2026-10000", None),
        decide("issues", ["Promotion"], ["Discipline"]),
        decide("summary", "Any paraphrase.", None),
    ] == ["accept", "reject", "edit", "accept"]


# log.debug("Defines the test that an export meets the contract and its decisions")
def test_a_replayed_export_meets_the_contract_and_follows_its_decisions() -> None:
    """The record is the truth; the deadline counts from the notice."""
    # log.debug("Replays the document")
    export = replay_case(RUN, _case())
    # log.debug("Checks the contract finds nothing wrong")
    assert [e.message for e in CONTRACT.iter_errors(export)] == []
    # log.debug("Checks the decisions, the record and the deadline")
    assert (
        export["decisions"]["charge_number"],
        export["decisions"]["issues"],
        export["record"]["charge_number"],
        export["record"]["issues"],
        export["response_due"],
    ) == ("reject", "edit", None, ["Discipline"], "2026-10-23")


# log.debug("Defines the test of the files written")
def test_each_run_is_one_file_of_its_documents_with_an_extraction(tmp_path: Path) -> None:
    """A failed document is left out, and a file holding no run too.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes a run of two documents, one failed")
    run = RUN | {"results": [_case("charge-000"), _case("charge-001", ok=False)]}
    # log.debug("Writes it where the live runs are")
    (tmp_path / "live-claude-sonnet-5-5-20261017T015121Z.json").write_text(json.dumps(run))
    # log.debug("Writes a file of the same pattern that holds no run")
    (tmp_path / "live-claude-sonnet-5-5-figures.json").write_text(json.dumps({"data": []}))
    # log.debug("Replays the folder")
    written = replay(tmp_path, tmp_path / "reviews")
    # log.debug("Checks one file of one line, for the document that succeeded")
    assert [len(p.read_text().splitlines()) for p in written] == [1]
