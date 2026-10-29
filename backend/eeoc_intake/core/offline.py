########################################################################
#                 backend/eeoc_intake/core/offline.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           An offline stand-in for the model that answers   #
#                     from each generated document's known values.     #
########################################################################
"""An offline stand-in for the model, for the smoke run and demo mode.

It answers from the known values `generate.py` wrote beside each
synthetic document, quoting the line of page text that carries each
value. One unsupported quote is planted in every two-respondent case,
so the run proves that verification empties what it cannot find. None
of this says how a real model performs; the live evaluation does.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Final

from kds.evals.case import EvalCase
from kds.llm import Message, ModelAdapter
from kds.llm.fake import FakeProvider
from kds.logs import get_logger
from kds.synthetic.pdftext import pages_text

from eeoc_intake.config import AppSettings
from eeoc_intake.core.schema import SCORED_FIELDS, Value

# Module constants
log = get_logger(__name__)
# log.debug("Sets the field whose quote is on the notice")
NOTICE_FIELD: Final = "notice_date"
# log.debug("Lists the date fields, written m/d/Y on the forms")
DATE_FIELDS: Final = frozenset({"earliest_date", "latest_date", NOTICE_FIELD})
# log.debug("Sets the tag of the hard case that names two respondents")
TWO_RESPONDENTS: Final = "two_respondents"
# log.debug("Sets the field that gets the planted unsupported quote")
PLANTED_FIELD: Final = "eeoc_office"
# log.debug("Sets the planted quote, which no document contains")
PLANTED_SPAN: Final = "this text is not in the document"
# log.debug("Maps an issue label to words the particulars use for it")
ISSUE_WORDS: Final = {"Terms/Conditions": "terms and conditions", "Discharge": "discharged"}
# log.debug("Sets the words the form prints beside a ticked continuing action")
CONTINUING_WORDS: Final = "CONTINUING ACTION"
# log.debug("Sets the confidence given to a value the stand-in fills")
SURE: Final = 0.9
# log.debug("Sets the confidence given to the stand-in's summary")
UNSURE: Final = 0.5
# log.debug("Lists the values that mean a field is empty")
EMPTY: Final[tuple[Value, ...]] = (None, "", [])
# log.debug("Sets the field that carries the charging party's name")
PARTY: Final = "charging_party"
# log.debug("Sets the separator of a written list")
LIST_SEP: Final = ", "
# log.debug("Names the field that lists the issues")
ISSUES_FIELD: Final = "issues"
# log.debug("Names the input that holds the charge's path")
CHARGE_PDF: Final = "charge_pdf"
# log.debug("Names the input that holds the notice's path")
NOTICE_PDF: Final = "notice_pdf"
# log.debug("Names a field's value key")
VALUE: Final = "value"
# log.debug("Names a field's quote key")
SPAN: Final = "span"
# log.debug("Names a field's page key")
PAGE: Final = "page"
# log.debug("Names a field's confidence key")
CONFIDENCE: Final = "confidence"
# log.debug("Sets the answer for a prompt about no known case")
NO_ANSWER: Final = "{}"
# log.debug("Names the provider setting that selects the stand-in")
FAKE: Final = "fake"
# log.debug("Names the stand-in's model in results and reviews")
STAND_IN: Final = "fake-model"


# log.debug("Defines the adapter: the stand-in in demo mode, else the real model")
def adapter_for(settings: AppSettings, cases: list[EvalCase]) -> ModelAdapter:
    """Return the stand-in for the fake provider, else the real one.

    Args:
        settings: The provider, model and budget to use.
        cases: The documents the stand-in can answer for.
    """
    # log.debug("Uses the stand-in when the provider is fake")
    if settings.llm_provider == FAKE:
        # log.debug("Returns an adapter that answers from the known values")
        return ModelAdapter(
            FakeProvider(responder=gold_responder(cases)), model=STAND_IN, settings=settings
        )
    # log.debug("Returns the configured provider")
    return ModelAdapter(settings=settings)


# log.debug("Defines the stand-in's answers for a set of cases")
def gold_responder(cases: list[EvalCase]) -> Callable[[list[Message]], str]:
    """Return a responder that answers each case from its values."""

    # log.debug("Defines the answer to one prompt")
    def respond(messages: list[Message]) -> str:
        """Return the record of the case the prompt is about."""
        # log.debug("Reads the prompt")
        text = messages[-1].content
        # log.debug("Finds the case whose charging party the prompt names")
        case = next((c for c in cases if c.expected[PARTY] in text), None)
        # log.debug("Returns an empty object for a prompt about no known case")
        if case is None:
            # log.debug("Returns no fields")
            return NO_ANSWER
        # log.debug("Returns the case's record as JSON")
        return json.dumps(gold_record(case))

    # log.debug("Returns the responder")
    return respond


# log.debug("Defines the record the stand-in gives for one case")
def gold_record(case: EvalCase) -> dict[str, Any]:
    """Return every field from the case's values, quoting the pages."""
    # log.debug("Reads the charge's pages")
    charge = pages_text(case.input[CHARGE_PDF])
    # log.debug("Reads the notice's pages")
    notice = pages_text(case.input[NOTICE_PDF])
    # log.debug("Builds each scored field with its quote and page")
    record = {
        name: _sourced(name, case.expected.get(name), notice if name == NOTICE_FIELD else charge)
        for name in SCORED_FIELDS
    }
    # log.debug("Plants an unsupported quote that verification must empty")
    if TWO_RESPONDENTS in case.tags:
        # log.debug("Replaces the office's quote with text no page holds")
        record[PLANTED_FIELD][SPAN] = PLANTED_SPAN
    # log.debug("Adds a one-sentence summary, which has no quote")
    record["summary"] = {
        VALUE: (
            f"{case.expected[PARTY]} alleges "
            f"{LIST_SEP.join(case.expected[ISSUES_FIELD]).lower()} "
            f"based on {LIST_SEP.join(case.expected['bases']).lower()}."
        ),
        PAGE: 1,
        SPAN: None,
        CONFIDENCE: UNSURE,
    }
    # log.debug("Returns the record")
    return record


# log.debug("Defines one field as the stand-in fills it")
def _sourced(name: str, value: Any, pages: list[str]) -> dict[str, Any]:
    """Return the value with the line that carries it, if any."""
    # log.debug("Finds the line of page text that carries the value")
    span = find_span(name, value, pages)
    # log.debug("Finds the first page that holds that line")
    page = next((i + 1 for i, p in enumerate(pages) if span and span in p), None)
    # log.debug("Returns the field, sure of a value and silent without one")
    return {
        VALUE: value,
        PAGE: page,
        SPAN: span,
        CONFIDENCE: SURE if value is not None else 0.0,
        "reason": None if value is not None else "not present in document",
    }


# log.debug("Defines how the stand-in finds the text behind a value")
def find_span(name: str, value: Any, pages: list[str]) -> str | None:
    """Return the line of page text that carries `value`, or None."""
    # log.debug("Returns no quote for an empty value")
    if value in EMPTY:
        # log.debug("Returns None")
        return None
    # log.debug("Works out the words to look for")
    probe = _probe(name, value)
    # log.debug("Looks for a whole line that holds the words")
    line = next(
        (
            line.strip()
            for page in pages
            for line in page.splitlines()
            if probe.casefold() in line.casefold()
        ),
        None,
    )
    # log.debug("Returns the line when there is one")
    if line is not None:
        # log.debug("Returns it")
        return line
    # log.debug("Matches across line breaks, where a value wraps in the page text")
    pattern = r"\s+".join(re.escape(word) for word in probe.split())
    # log.debug("Returns the first wrapped match, or None")
    return next(
        (
            match.group(0)
            for page in pages
            if (match := re.search(pattern, page, flags=re.IGNORECASE))
        ),
        None,
    )


# log.debug("Defines the words a value appears as on the page")
def _probe(name: str, value: Any) -> str:
    """Return the value as the documents print it."""
    # log.debug("Takes a list's first item, or the value as text")
    probe = value[0] if isinstance(value, list) else str(value)
    # log.debug("Uses the particulars' own words for an issue")
    if name == ISSUES_FIELD:
        # log.debug("Swaps the label for those words, when they differ")
        probe = ISSUE_WORDS.get(probe, probe)
    # log.debug("Writes a date the way the forms do, month first")
    if name in DATE_FIELDS:
        # log.debug("Splits the ISO date")
        year, month, day = str(value).split("-")
        # log.debug("Reorders it")
        probe = f"{month}/{day}/{year}"
    # log.debug("Looks for the ticked box's label for a continuing action")
    if name == "continuing_action":
        # log.debug("Uses the box's label")
        probe = CONTINUING_WORDS
    # log.debug("Returns the words")
    return probe
