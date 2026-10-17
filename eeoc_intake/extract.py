"""Extraction: PDF pages in, a ChargeRecord with evidence out, then span verification.

`extract()` returns everything a reviewer or an evaluation needs to judge the result: the verified record, the
raw model output, the list of fields verification emptied, the page texts the spans point into, and what the
call cost.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from kds.llm.adapter import ModelAdapter
from kds.logs import get_logger, log_event
from kds.synthetic.pdftext import pages_text, span_in_page

from eeoc_intake.schema import FIELDS, ChargeRecord, Sourced

_log = get_logger("eeoc.extract")

SYSTEM = """You extract fields from an EEOC charge of discrimination and its notice letter.

Rules:
- For every field, quote the exact text that supports the value as `span`, copied character for character from
  the page text, and give the 1-based `page` it appears on. A span is a short excerpt: a line or a phrase,
  never a whole paragraph.
- The charge pages come first; `page` for every field refers to the CHARGE document, except `notice_date`,
  whose `page` refers to the NOTICE document.
- If the document does not support a value, leave `value` null, set `confidence` to 0 and explain in `reason`.
  Never guess. A blank line where a value should be means the value is missing.
- Dates are ISO (YYYY-MM-DD). `bases` is the list of protected bases as written on the form. `respondent` is a
  single string, or a list when the charge names more than one.
- `issues` is the list of employment actions the particulars describe, using the EEOC labels: Discharge,
  Harassment, Terms/Conditions, Promotion, Discipline, Reasonable Accommodation. The particulars describe what
  happened in plain words (a denied promotion, a written warning, a termination); map each to its label and
  quote the sentence that describes it. Leave `issues` empty only if the particulars describe no action.
- `continuing_action` is true only if the form marks it; otherwise false with no span.
- `summary` is at most three sentences, drawn only from the particulars; it has no span.
- `confidence` is your own estimate from 0 to 1 that the value is correct."""


@dataclass
class Extraction:
    record: ChargeRecord
    raw: ChargeRecord
    removed: list[str] = field(default_factory=list)
    charge_pages: list[str] = field(default_factory=list)
    notice_pages: list[str] = field(default_factory=list)
    model: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


def build_prompt(charge_pages: list[str], notice_pages: list[str]) -> str:
    parts = ["=== CHARGE ==="]
    for i, p in enumerate(charge_pages, start=1):
        parts.append(f"--- page {i} ---\n{p}")
    parts.append("=== NOTICE ===")
    for i, p in enumerate(notice_pages, start=1):
        parts.append(f"--- page {i} (notice) ---\n{p}")
    parts.append("Extract the fields.")
    return "\n".join(parts)


def extract(adapter: ModelAdapter, charge_pdf: Path | str, notice_pdf: Path | str) -> Extraction:
    charge_pages = pages_text(charge_pdf)
    notice_pages = pages_text(notice_pdf)
    t0 = time.perf_counter()
    raw, completion = adapter.complete_json(
        build_prompt(charge_pages, notice_pages), ChargeRecord, system=SYSTEM
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    verified, removed = verify_spans(raw, charge_pages, notice_pages)
    log_event(
        _log,
        "extract.done",
        charge=str(charge_pdf),
        filled=sum(1 for f in FIELDS if getattr(verified, f).value not in (None, "", [])),
        removed=removed,
        cost_usd=completion.cost_usd,
        latency_ms=latency_ms,
    )
    return Extraction(
        record=verified,
        raw=raw,
        removed=removed,
        charge_pages=charge_pages,
        notice_pages=notice_pages,
        model=completion.model,
        cost_usd=completion.cost_usd or 0.0,
        latency_ms=latency_ms,
    )


def verify_spans(
    record: ChargeRecord, charge_pages: list[str], notice_pages: list[str]
) -> tuple[ChargeRecord, list[str]]:
    """Empty any field whose quoted span is not on the page it cites. The reviewer never sees unsupported values.

    Returns the verified record and the names of the fields that were emptied.
    """
    out = record.model_copy(deep=True)
    removed: list[str] = []
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
            removed.append(f)
            setattr(
                out,
                f,
                Sourced(value=None, reason="unsupported: cited span not found on cited page", confidence=0.0),
            )
    return out, removed


def response_due(notice_date: date, days: int = 30) -> date:
    """A rule, not a model output: the position statement is typically due 30 days after the notice date."""
    return notice_date + timedelta(days=days)
