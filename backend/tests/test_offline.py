########################################################################
#                    backend/tests/test_offline.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the offline stand-in: it quotes the pages, and its planted quote
is emptied by the check.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path

# Third-party
from kds.args import required
from kds.evals.case import load_cases
from kds.logs import get_logger

# Local
from eeoc_intake.config import AppSettings
from eeoc_intake.core.extract import extract
from eeoc_intake.core.generate import generate
from eeoc_intake.core.offline import PLANTED_FIELD, adapter_for, find_span, gold_record

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                            Stand-in tests                            #
########################################################################
# log.debug("Defines the test: a date is found as the form prints it")
def test_a_date_is_found_as_the_form_prints_it() -> None:
    """Checks dates are looked for month first, as forms print them."""
    # log.debug("Looks for a notice date")
    span = find_span("notice_date", "2026-03-02", ["To: X\nDate of Notice: 03/02/2026\n"])
    # log.debug("Checks the whole line is quoted")
    assert span == "Date of Notice: 03/02/2026"


# log.debug("Defines the test: a value that wraps is quoted across the break")
def test_a_value_that_wraps_is_quoted_across_the_break() -> None:
    """Checks a value that wraps is quoted across the line break."""
    # log.debug("Looks for a value split over two lines")
    span = find_span("respondent", "Acme Logistics Group", ["Respondent: Acme\nLogistics Group\n"])
    # log.debug("Checks the words are quoted with the break inside")
    assert span == "Acme\nLogistics Group"


# log.debug("Defines the test: the stand in answers from the known values")
def test_the_stand_in_answers_from_the_known_values(settings: AppSettings) -> None:
    """Checks the stand-in's record matches the case; every quote holds.

    Args:
        settings: Offline settings over the ten samples.
    """
    # log.debug("Loads the samples")
    cases = load_cases(settings.data_samples / "cases.jsonl")
    # log.debug("Extracts the first through the stand-in")
    ex = extract(adapter_for(settings, cases), **_documents(cases[0].input))
    # log.debug("Checks the party matches and nothing was emptied")
    assert ex.record.charging_party.value == cases[0].expected["charging_party"]
    # log.debug("Checks no field was emptied and the stand-in cost nothing")
    assert ex.removed == [] and ex.model == "fake-model"


# log.debug("Defines the test: the planted quote is emptied")
def test_the_planted_quote_is_emptied(settings: AppSettings, tmp_path: Path) -> None:
    """Checks the planted quote, on no page, is emptied before review.

    Args:
        settings: Offline settings over the ten samples.
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Generates twenty cases, so a two-respondent case exists")
    cases = load_cases(_twenty(tmp_path))
    # log.debug("Finds that case")
    case = next(c for c in cases if c.tags == ["two_respondents"])
    # log.debug("Checks the stand-in planted the quote")
    assert gold_record(case)[PLANTED_FIELD]["span"] == "this text is not in the document"
    # log.debug("Extracts the case")
    ex = extract(adapter_for(settings, cases), **_documents(case.input))
    # log.debug("Checks verification emptied exactly that field")
    assert ex.removed == [PLANTED_FIELD] and ex.record.eeoc_office.value is None


# log.debug("Defines a case's input as extract()'s keyword arguments")
def _documents(given: dict[str, str] | None = None) -> dict[str, str]:
    """Returns a case's input as extract()'s keyword arguments.

    Args:
        given: The case's input, as cases.jsonl holds it. Required.

    Returns:
        The paths of the charge and the notice, by argument name.
    """
    # log.debug("Takes the given, which the caller must give")
    given = required(given=given)
    # log.debug("Returns the two paths")
    return {"charge_pdf": given["charge_pdf"], "notice_pdf": given["notice_pdf"]}


# log.debug("Defines twenty generated cases in a test's folder")
def _twenty(tmp_path: Path | None = None) -> Path:
    """Generates twenty cases into tmp_path; return the cases file.

    Args:
        tmp_path: The test's temporary folder. Required.

    Returns:
        The cases file.
    """
    # log.debug("Takes the tmp path, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Generates and returns the file")
    return generate(AppSettings(samples_count=20, samples_seed=3), tmp_path / "twenty")
