"""Span verification: a value the document does not support never reaches the reviewer."""

from datetime import date

from eeoc_intake.extract import response_due, verify_spans
from eeoc_intake.schema import ChargeRecord, Sourced

CHARGE = ["CHARGE OF DISCRIMINATION\nCharge No. 410-2026-10001\nCharging Party: Ada Lovelace\n"]
NOTICE = ["NOTICE OF CHARGE\nDate of Notice: 03/02/2026\n"]


def test_supported_span_is_kept():
    rec = ChargeRecord(
        charge_number=Sourced(value="410-2026-10001", page=1, span="Charge No.  410-2026-10001")
    )
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.charge_number.value == "410-2026-10001"
    assert removed == []


def test_unsupported_span_is_emptied_with_reason():
    rec = ChargeRecord(charging_party=Sourced(value="Ada Lovelace", page=1, span="Complainant: Ada Lovelace"))
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.charging_party.value is None
    assert out.charging_party.confidence == 0.0
    assert "unsupported" in (out.charging_party.reason or "")
    assert removed == ["charging_party"]


def test_wrong_page_is_unsupported():
    rec = ChargeRecord(
        charge_number=Sourced(value="410-2026-10001", page=2, span="Charge No. 410-2026-10001")
    )
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.charge_number.value is None
    assert removed == ["charge_number"]


def test_notice_date_is_checked_against_the_notice():
    rec = ChargeRecord(notice_date=Sourced(value="2026-03-02", page=1, span="Date of Notice: 03/02/2026"))
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.notice_date.value == "2026-03-02"
    assert removed == []


def test_false_checkbox_and_summary_need_no_span():
    rec = ChargeRecord(
        continuing_action=Sourced(value=False),
        summary=Sourced(value="A short summary.", confidence=0.5),
    )
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.continuing_action.value is False
    assert out.summary.value == "A short summary."
    assert removed == []


def test_true_checkbox_needs_evidence():
    rec = ChargeRecord(continuing_action=Sourced(value=True, page=1, span="[X] CONTINUING ACTION"))
    out, removed = verify_spans(rec, CHARGE, NOTICE)
    assert out.continuing_action.value is None
    assert removed == ["continuing_action"]


def test_response_due_is_thirty_days_after_notice():
    assert response_due(date(2026, 3, 2)) == date(2026, 4, 1)
