########################################################################
#                    backend/tests/test_generate.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests that generated documents repeat for a seed and print the values
their answers claim.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from pathlib import Path

# Third-party
from kds.args import required
from kds.logs import get_logger
from kds.synthetic.pdftext import pages_text

# Local
from eeoc_intake.config import AppSettings
from eeoc_intake.core.charges import HARD_KINDS, kind_of
from eeoc_intake.core.generate import generate

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                           Generator tests                            #
########################################################################
# log.debug("Defines how the cases a generated folder holds are read")
def _cases(folder: Path | None = None) -> list[dict[str, object]]:
    """Returns the cases a generated folder holds.

    Args:
        folder: The folder of generated documents. Required.

    Returns:
        Each case in the folder's cases.jsonl.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Reads one case per line")
    return [json.loads(line) for line in (folder / "cases.jsonl").read_text().splitlines()]


# log.debug("Defines the test: every fifth document is a hard case in turn")
def test_every_fifth_document_is_a_hard_case_in_turn() -> None:
    """Checks positions 4, 9, 14 and 19 are the hard kinds, in order."""
    # log.debug("Checks the kinds of the first twenty positions")
    assert [kind_of(i, 5) for i in range(4, 20, 5)] == list(HARD_KINDS)
    # log.debug("Checks the others are clean")
    assert {kind_of(i, 5) for i in range(20) if i % 5 != 4} == {"clean"}


# log.debug("Defines the test: the same seed makes the same set")
def test_the_same_seed_makes_the_same_set(tmp_path: Path) -> None:
    """Checks two runs from one seed give the same answers and pages.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Generates the same small set twice")
    first, second = (
        generate(AppSettings(samples_count=6, samples_seed=11), tmp_path / name).parent
        for name in ("a", "b")
    )
    # log.debug("Checks the known answers match")
    assert [c["expected"] for c in _cases(first)] == [c["expected"] for c in _cases(second)]
    # log.debug("Checks a document's text matches")
    assert pages_text(first / "charge-005.pdf") == pages_text(second / "charge-005.pdf")


# log.debug("Defines the test: the documents print what the answers claim")
def test_the_documents_print_what_the_answers_claim(samples: Path) -> None:
    """Checks each document prints what its answers claim.

    Args:
        samples: The folder of the session's ten generated samples.
    """
    # log.debug("Reads the first case")
    case = _cases(samples)[0]
    # log.debug("Reads its known answers")
    expected = case["expected"]
    # log.debug("Checks the answers are a mapping")
    assert isinstance(expected, dict)
    # log.debug("Reads the charge's first page")
    charge = pages_text(samples / "charge-000.pdf")[0]
    # log.debug("Checks the number and the party are printed")
    assert expected["charge_number"] in charge and expected["charging_party"] in charge
    # log.debug("Reads the notice")
    notice = pages_text(samples / "notice-000.pdf")[0]
    # log.debug("Checks its date is printed month first")
    year, month, day = str(expected["notice_date"]).split("-")
    # log.debug("Checks the date")
    assert f"{month}/{day}/{year}" in notice


# log.debug("Defines the test: the hard cases are what their tags say")
def test_the_hard_cases_are_what_their_tags_say(samples: Path) -> None:
    """Checks the fifth has no number and the tenth's first page turns.

    Args:
        samples: The folder of the session's ten generated samples.
    """
    # log.debug("Reads the cases")
    cases = _cases(samples)
    # log.debug("Checks the kinds")
    assert [cases[4]["tags"], cases[9]["tags"]] == [["missing_number"], ["rotated"]]
    # log.debug("Reads the fifth's known answers")
    expected = cases[4]["expected"]
    # log.debug("Checks it has no number")
    assert isinstance(expected, dict) and expected["charge_number"] is None
