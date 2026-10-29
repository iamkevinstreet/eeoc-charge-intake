########################################################################
#               backend/src/eeoc_intake/core/extract.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Reads a charge and its notice into a record with evidence, then empties
what the pages don't say.

`extract()` returns everything a reviewer or an evaluation needs to
judge the result: the verified record, the raw model output, the
fields verification emptied, the page texts the quotes point into,
and what the call cost.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Final

# Third-party
from kds.args import missing, required
from kds.llm import ModelAdapter
from kds.logs import get_logger, log_event
from kds.synthetic.pdftext import pages_text, span_in_page
from pypdf.errors import PyPdfError

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.core.schema import FIELDS, ChargeRecord, Sourced, is_empty

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the field whose quote is on the notice, not the charge, from the config")
NOTICE_FIELD: Final = SETTINGS.record_notice_field
# log.debug("Takes the field that paraphrases, so it has no quote to check, from the config")
SUMMARY_FIELD: Final = SETTINGS.record_summary_field
# log.debug("Takes the milliseconds in a second, from the config")
MS: Final = SETTINGS.units_ms_per_second

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the instructions the model reads before the documents")
SYSTEM: Final = (
    "You extract fields from an EEOC charge of discrimination and its notice letter.\n"
    "\n"
    "Rules:\n"
    "- For every field, quote the exact text that supports the value as `span`, copied "
    "character for character from\n"
    "  the page text, and give the 1-based `page` it appears on. A span is a short excerpt: "
    "a line or a phrase,\n"
    "  never a whole paragraph.\n"
    "- The charge pages come first; `page` for every field refers to the CHARGE document, "
    "except `notice_date`,\n"
    "  whose `page` refers to the NOTICE document.\n"
    "- If the document does not support a value, leave `value` null, set `confidence` to 0 "
    "and explain in `reason`.\n"
    "  Never guess. A blank line where a value should be means the value is missing.\n"
    "- Dates are ISO (YYYY-MM-DD). `bases` is the list of protected bases as written on the "
    "form. `respondent` is a\n"
    "  single string, or a list when the charge names more than one.\n"
    "- `issues` is the list of employment actions the particulars describe, using the EEOC "
    "labels: Discharge,\n"
    "  Harassment, Terms/Conditions, Promotion, Discipline, Reasonable Accommodation. The "
    "particulars describe what\n"
    "  happened in plain words (a denied promotion, a written warning, a termination); map "
    "each to its label and\n"
    "  quote the sentence that describes it. Leave `issues` empty only if the particulars "
    "describe no action.\n"
    "- `continuing_action` is true only if the form marks it; otherwise false with no span.\n"
    "- `summary` is at most three sentences, drawn only from the particulars; it has no span.\n"
    "- `confidence` is your own estimate from 0 to 1 that the value is correct."
)
# log.debug("Sets the reason a field emptied by verification carries")
UNSUPPORTED: Final = "unsupported: cited span not found on cited page"


########################################################################
#                              Extraction                              #
########################################################################
# log.debug("Defines the error for a document whose text cannot be read")
class UnreadableDocumentError(ValueError):
    """A PDF the reader could not read, so no model call is made."""


# log.debug("Defines what one extraction returns")
@dataclass
class Extraction:
    """A verified record, the raw output, and what the call cost.

    Attributes:
        record: The record after verification; what a reviewer sees.
        raw: The model's record before verification.
        removed: The fields verification emptied.
        charge_pages: The charge's page texts, which quotes point into.
        notice_pages: The notice's page texts.
        model: The model that answered.
        cost_usd: What the call cost, at list prices.
        latency_ms: How long the call took.
    """

    # log.debug("Holds the verified record")
    record: ChargeRecord
    # log.debug("Holds the model's own record")
    raw: ChargeRecord
    # log.debug("Holds the fields verification emptied")
    removed: list[str] = field(default_factory=list)
    # log.debug("Holds the charge's page texts")
    charge_pages: list[str] = field(default_factory=list)
    # log.debug("Holds the notice's page texts")
    notice_pages: list[str] = field(default_factory=list)
    # log.debug("Holds the model's name")
    model: str = ""
    # log.debug("Holds the call's cost")
    cost_usd: float = 0.0
    # log.debug("Holds the call's time")
    latency_ms: int = 0


# log.debug("Defines the prompt: every page of both documents, numbered")
def build_prompt(
    charge_pages: list[str] | None = None, notice_pages: list[str] | None = None
) -> str:
    """Returns the charge's pages, the notice's, then the request.

    Args:
        charge_pages: The charge's page texts, in order. Required.
        notice_pages: The notice's page texts, in order. Required.

    Returns:
        The prompt: each document's pages under their numbers, then
        the request.
    """
    # log.debug("Takes the charge pages, which the caller must give")
    charge_pages = required(charge_pages=charge_pages)
    # log.debug("Takes the notice pages, which the caller must give")
    notice_pages = required(notice_pages=notice_pages)
    # log.debug("Starts with the charge's heading")
    parts = ["=== CHARGE ==="]
    # log.debug("Adds each charge page under its number")
    parts += [f"--- page {i} ---\n{p}" for i, p in enumerate(charge_pages, start=1)]
    # log.debug("Adds the notice's heading")
    parts.append("=== NOTICE ===")
    # log.debug("Adds each notice page under its number")
    parts += [f"--- page {i} (notice) ---\n{p}" for i, p in enumerate(notice_pages, start=1)]
    # log.debug("Ends with the request")
    parts.append("Extract the fields.")
    # log.debug("Returns the parts, one per line")
    return "\n".join(parts)


# log.debug("Defines one extraction")
def extract(
    adapter: ModelAdapter | None = None,
    charge_pdf: Path | str | None = None,
    notice_pdf: Path | str | None = None,
) -> Extraction:
    """Reads both PDFs, asks the model for the record, checks quotes.

    Args:
        adapter: The model adapter to call. Required.
        charge_pdf: The charge form's PDF. Required.
        notice_pdf: The notice letter's PDF. Required.

    Returns:
        The checked record, the model's own record, the fields the
        check emptied, both documents' page texts, and the model, cost
        and time of the call.

    Raises:
        UnreadableDocumentError: A PDF could not be read.
        kds.llm.errors.StructuredOutputError: The answer did not fit the
            record, even after one repair.
    """
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Stops when the caller left out the charge's PDF")
    if charge_pdf is None:
        # log.debug("Raises the missing-argument error")
        raise missing(charge_pdf=charge_pdf)
    # log.debug("Stops when the caller left out the notice's PDF")
    if notice_pdf is None:
        # log.debug("Raises the missing-argument error")
        raise missing(notice_pdf=notice_pdf)
    # log.debug("Reads the charge's text, page by page")
    charge_pages = read_pages(charge_pdf)
    # log.debug("Reads the notice's text, page by page")
    notice_pages = read_pages(notice_pdf)
    # log.debug("Notes the spend so far, so a repair call is counted too")
    spent = adapter.spent_usd
    # log.debug("Starts the clock")
    started = time.perf_counter()
    # log.debug("Asks the model for the record, with the schema enforced")
    raw, completion = adapter.complete_json(
        build_prompt(charge_pages, notice_pages), ChargeRecord, system=SYSTEM
    )
    # log.debug("Measures the whole exchange, a repair included")
    latency_ms = int((time.perf_counter() - started) * MS)
    # log.debug("Measures what the exchange cost")
    cost_usd = adapter.spent_usd - spent
    # log.debug("Empties every field whose quote is not on the page it cites")
    verified, removed = verify_spans(raw, charge_pages, notice_pages)
    # log.debug("Logs how many fields were filled and which were emptied")
    log_event(
        log,
        "extract.done",
        filled=sum(1 for f in FIELDS if not is_empty(verified.sourced(f).value)),
        removed=removed,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    # log.debug("Returns the record, the raw answer and the call's facts")
    return Extraction(
        record=verified,
        raw=raw,
        removed=removed,
        charge_pages=charge_pages,
        notice_pages=notice_pages,
        model=completion.model,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


# log.debug("Defines reading a PDF's pages, with a clear error for a bad file")
def read_pages(path: Path | str | None = None) -> list[str]:
    """Returns each page's text.

    Args:
        path: The PDF to read. Required.

    Returns:
        Each page's text, in order.

    Raises:
        UnreadableDocumentError: The file is not a PDF the reader can
            open, or its text cannot be extracted.
    """
    # log.debug("Stops when the caller left out the path")
    if path is None:
        # log.debug("Raises the missing-argument error")
        raise missing(path=path)
    # log.debug("Reads the pages")
    try:
        # log.debug("Returns each page's text")
        return pages_text(path)
    except PyPdfError as error:
        # log.debug("Raises a plain error that names no path")
        msg = "the PDF could not be read"
        # log.debug("Raises it, keeping the reader's error as the cause")
        raise UnreadableDocumentError(msg) from error


# log.debug("Defines the check that keeps unsupported values from a reviewer")
def verify_spans(
    record: ChargeRecord | None = None,
    charge_pages: list[str] | None = None,
    notice_pages: list[str] | None = None,
) -> tuple[ChargeRecord, list[str]]:
    """Empties any field whose quote is not on the page it cites.

    The reviewer never sees an unsupported value. A summary is a
    paraphrase, judged separately; an unticked box (False) has nothing
    to quote.

    Args:
        record: The record as the model gave it, left unchanged.
            Required.
        charge_pages: The charge's page texts. Required.
        notice_pages: The notice's page texts. Required.

    Returns:
        The verified record and the names of the fields emptied.
    """
    # log.debug("Takes the record, which the caller must give")
    record = required(record=record)
    # log.debug("Takes the charge pages, which the caller must give")
    charge_pages = required(charge_pages=charge_pages)
    # log.debug("Takes the notice pages, which the caller must give")
    notice_pages = required(notice_pages=notice_pages)
    # log.debug("Copies the record, so the raw answer stays as it came")
    out = record.model_copy(deep=True)
    # log.debug("Starts the list of emptied fields")
    removed: list[str] = []
    # log.debug("Checks each field in turn")
    for name in FIELDS:
        # log.debug("Reads the field")
        sourced = out.sourced(name)
        # log.debug("Skips fields with nothing to check")
        if not _checkable(name, sourced):
            # log.debug("Moves to the next field")
            continue
        # log.debug("Picks the document the field's page refers to")
        pages = notice_pages if name == NOTICE_FIELD else charge_pages
        # log.debug("Keeps the field when its quote is on its page")
        if _quoted(sourced, pages):
            # log.debug("Moves to the next field")
            continue
        # log.debug("Records the field as emptied")
        removed.append(name)
        # log.debug("Empties it, saying why")
        setattr(out, name, Sourced(value=None, reason=UNSUPPORTED, confidence=0.0))
    # log.debug("Returns the verified record and the emptied fields")
    return out, removed


# log.debug("Defines which fields have a quote to check")
def _checkable(name: str | None = None, sourced: Sourced | None = None) -> bool:
    """Returns True for a filled field that must quote its evidence.

    Args:
        name: The field's name. Required.
        sourced: The field. Required.

    Returns:
        False for an empty field, the summary and an unticked box, and
        True for every other field.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the field, which the caller must give")
    sourced = required(sourced=sourced)
    # log.debug("Returns False for empty fields, the summary and an unticked box")
    return not (is_empty(sourced.value) or name == SUMMARY_FIELD or sourced.value is False)


# log.debug("Defines whether a quote is on the page it cites")
def _quoted(sourced: Sourced | None = None, pages: list[str] | None = None) -> bool:
    """Returns True when the span is on the cited page of `pages`.

    Args:
        sourced: The field, with its quote and page. Required.
        pages: The page texts of the document the page refers to.
            Required.

    Returns:
        True when the cited page exists and holds the quote, case and
        spacing aside.
    """
    # log.debug("Takes the field, which the caller must give")
    sourced = required(sourced=sourced)
    # log.debug("Takes the pages, which the caller must give")
    pages = required(pages=pages)
    # log.debug("Returns False without a quote or a page")
    if sourced.span is None or sourced.page is None:
        # log.debug("Returns False")
        return False
    # log.debug("Returns whether the page exists and holds the quote")
    return 1 <= sourced.page <= len(pages) and span_in_page(sourced.span, pages[sourced.page - 1])


# log.debug("Defines the response deadline, a rule rather than a model output")
def response_due(notice_date: date | None = None, days: int | None = None) -> date:
    """Returns the day a position statement is typically due.

    Args:
        notice_date: The date of the EEOC's notice. Required.
        days: The days allowed, from `[extract] response_days`.
            Required.

    Returns:
        The notice date plus the days allowed.
    """
    # log.debug("Takes the notice date, which the caller must give")
    notice_date = required(notice_date=notice_date)
    # log.debug("Takes the days, which the caller must give")
    days = required(days=days)
    # log.debug("Returns the notice date plus the days allowed")
    return notice_date + timedelta(days=days)
