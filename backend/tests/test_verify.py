########################################################################
#                     backend/tests/test_verify.py                     #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests that a value the document does not support #
#                     never reaches the reviewer.                      #
########################################################################
"""Tests of quote verification and the response deadline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from kds.logs import get_logger

from eeoc_intake.core.extract import (
    UnreadableDocumentError,
    read_pages,
    response_due,
    verify_spans,
)
from eeoc_intake.core.schema import ChargeRecord, Sourced

# Module constants
log = get_logger(__name__)
# log.debug("Sets a one-page charge")
CHARGE = ["CHARGE OF DISCRIMINATION\nCharge No. 410-2026-10001\nCharging Party: Ada Lovelace\n"]
# log.debug("Sets a one-page notice")
NOTICE = ["NOTICE OF CHARGE\nDate of Notice: 03/02/2026\n"]
# log.debug("Sets the charge number the charge prints")
NUMBER = "410-2026-10001"


# log.debug("Defines the test: a supported quote is kept")
def test_a_supported_quote_is_kept() -> None:
    """Spacing and case aside, the quote is on its page, so it stays."""
    # log.debug("Builds a record whose quote is on page one, spaced oddly")
    rec = ChargeRecord(charge_number=Sourced(value=NUMBER, page=1, span=f"Charge No.  {NUMBER}"))
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks the value stayed and nothing was emptied")
    assert out.charge_number.value == NUMBER and removed == []


# log.debug("Defines the test: an unsupported quote is emptied with a reason")
def test_an_unsupported_quote_is_emptied_with_a_reason() -> None:
    """A quote not on the page empties the field and says why."""
    # log.debug("Builds a record whose quote is not in the document")
    rec = ChargeRecord(
        charging_party=Sourced(value="Ada Lovelace", page=1, span="Complainant: Ada Lovelace")
    )
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks the value is gone, with no confidence")
    assert out.charging_party.value is None and out.charging_party.confidence == 0.0
    # log.debug("Checks the reason and the list of emptied fields")
    assert "unsupported" in (out.charging_party.reason or "")
    # log.debug("Checks the field is listed as emptied")
    assert removed == ["charging_party"]


# log.debug("Defines the test: a quote on the wrong page is unsupported")
def test_a_quote_on_the_wrong_page_is_unsupported() -> None:
    """The quote must be on the page cited, not just anywhere."""
    # log.debug("Builds a record citing a page the charge does not have")
    rec = ChargeRecord(charge_number=Sourced(value=NUMBER, page=2, span=f"Charge No. {NUMBER}"))
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks it was emptied")
    assert out.charge_number.value is None and removed == ["charge_number"]


# log.debug("Defines the test: the notice date is checked against the notice")
def test_the_notice_date_is_checked_against_the_notice() -> None:
    """The one field quoted from the notice is checked in the notice."""
    # log.debug("Builds a record with the notice date quoted")
    rec = ChargeRecord(
        notice_date=Sourced(value="2026-03-02", page=1, span="Date of Notice: 03/02/2026")
    )
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks it stayed")
    assert out.notice_date.value == "2026-03-02" and removed == []


# log.debug("Defines the test: an unticked box and the summary need no quote")
def test_an_unticked_box_and_the_summary_need_no_quote() -> None:
    """False has nothing to quote; a summary is judged on its own."""
    # log.debug("Builds a record with an unticked box and a summary")
    rec = ChargeRecord(
        continuing_action=Sourced(value=False),
        summary=Sourced(value="A short summary.", confidence=0.5),
    )
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks both stayed")
    assert out.continuing_action.value is False and out.summary.value == "A short summary."
    # log.debug("Checks nothing was emptied")
    assert removed == []


# log.debug("Defines the test: a ticked box needs evidence")
def test_a_ticked_box_needs_evidence() -> None:
    """True claims the form marks it, so the mark must be quoted."""
    # log.debug("Builds a record claiming a tick the page does not show")
    rec = ChargeRecord(continuing_action=Sourced(value=True, page=1, span="[X] CONTINUING ACTION"))
    # log.debug("Verifies it")
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    # log.debug("Checks it was emptied")
    assert out.continuing_action.value is None and removed == ["continuing_action"]


# log.debug("Defines the test: the response is due the given days after the notice")
def test_the_response_is_due_the_given_days_after_the_notice() -> None:
    """Thirty days after March 2 is April 1."""
    # log.debug("Checks the deadline")
    assert response_due(date(2026, 3, 2), 30) == date(2026, 4, 1)


# log.debug("Defines the test: a file that is not a pdf is unreadable")
def test_a_file_that_is_not_a_pdf_is_unreadable(tmp_path: Path) -> None:
    """A clear error, before any model is called."""
    # log.debug("Writes a file that only looks like a PDF")
    bad = tmp_path / "bad.pdf"
    # log.debug("Writes it")
    bad.write_bytes(b"%PDF-1.4 and nothing else")
    # log.debug("Checks reading it raises the plain error")
    with pytest.raises(UnreadableDocumentError):
        # log.debug("Reads it")
        read_pages(bad)
