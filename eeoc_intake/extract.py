"""Extraction: PDF pages in, a ChargeRecord with evidence out, then span verification."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from kds.llm.adapter import ModelAdapter
from kds.logs import get_logger, log_event
from kds.synthetic.pdftext import pages_text, span_in_page

from eeoc_intake.schema import FIELDS, ChargeRecord, Sourced

_log = get_logger("eeoc.extract")

SYSTEM = """You extract fields from an EEOC charge of discrimination and its notice letter.
Rules:
- For every field, quote the exact text (the span) and the 1-based page number that supports the value.
- If the document does not support a value, leave value empty and give the reason. Never guess.
- Dates are ISO (YYYY-MM-DD). `bases` and `issues` are lists. `respondent` is a list if there are several.
- `continuing_action` is true only if the form marks it.
- `summary` is three sentences at most, drawn only from the particulars."""


def build_prompt(charge_pages: list[str], notice_pages: list[str]) -> str:
    parts = ["=== CHARGE ==="]
    for i, p in enumerate(charge_pages, start=1):
        parts.append(f"--- page {i} ---\n{p}")
    parts.append("=== NOTICE ===")
    for i, p in enumerate(notice_pages, start=1):
        parts.append(f"--- page {i} (notice) ---\n{p}")
    parts.append("Extract the fields.")
    return "\n".join(parts)


def extract(adapter: ModelAdapter, charge_pdf: Path | str, notice_pdf: Path | str) -> ChargeRecord:
    charge_pages = pages_text(charge_pdf)
    notice_pages = pages_text(notice_pdf)
    record, completion = adapter.complete_json(
        build_prompt(charge_pages, notice_pages), ChargeRecord, system=SYSTEM
    )
    verified = verify_spans(record, charge_pages, notice_pages)
    log_event(
        _log,
        "extract.done",
        charge=str(charge_pdf),
        filled=sum(1 for f in FIELDS if getattr(verified, f).value not in (None, "", [])),
        cost_usd=completion.cost_usd,
    )
    return verified


def verify_spans(record: ChargeRecord, charge_pages: list[str], notice_pages: list[str]) -> ChargeRecord:
    """Empty any field whose quoted span is not on the page it cites. The reviewer never sees unsupported values."""
    out = record.model_copy(deep=True)
    for f in FIELDS:
        s: Sourced = getattr(out, f)
        if s.value in (None, "", []):
            continue
        if f == "summary":
            continue  # a summary is a paraphrase; it is judged separately
        if s.value is False:
            continue  # an unticked box has no span to quote; False is the default, True needs evidence
        pages = notice_pages if f == "notice_date" else charge_pages
        ok = (
            s.span is not None
            and s.page is not None
            and 1 <= s.page <= len(pages)
            and span_in_page(s.span, pages[s.page - 1])
        )
        if not ok:
            setattr(
                out,
                f,
                Sourced(value=None, reason="unsupported: cited span not found on cited page", confidence=0.0),
            )
    return out


def response_due(notice_date: date, days: int = 30) -> date:
    """A rule, not a model output: the position statement is typically due 30 days after the notice date."""
    return notice_date + timedelta(days=days)
