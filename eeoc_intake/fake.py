"""An offline stand-in for the model, used by the smoke evaluation and by the demo mode of the review service.

It answers from the ground truth that `generate.py` wrote next to each synthetic document, quoting the line
of page text that carries each value. One unsupported span is planted in every `two_respondents` case so the
run proves that span verification empties what it cannot find. None of this says anything about how a real
model performs; that is what the live evaluation is for.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from kds.evals.case import EvalCase
from kds.llm.types import Message
from kds.synthetic.pdftext import pages_text

from eeoc_intake.schema import FIELDS

SCORED_FIELDS = [f for f in FIELDS if f != "summary"]


def gold_responder(cases: list[EvalCase]) -> Callable[[list[Message]], str]:
    """Build a responder that answers the prompt for any of `cases` from its expected values."""

    def respond(messages: list[Message]) -> str:
        text = messages[-1].content
        for c in cases:
            if c.expected["charging_party"] not in text:
                continue
            pages = pages_text(c.input["charge_pdf"])
            record: dict = {}
            for f in SCORED_FIELDS:
                value = c.expected.get(f)
                span = find_span(f, value, pages)
                page = next((i + 1 for i, p in enumerate(pages) if span and span in p), None)
                if f == "notice_date":
                    page, span = 1, "Date of Notice"
                record[f] = {
                    "value": value,
                    "page": page,
                    "span": span,
                    "confidence": 0.9 if value is not None else 0.0,
                    "reason": None if value is not None else "not present in document",
                }
            if "two_respondents" in c.tags:  # planted unsupported span: verification must empty it
                record["eeoc_office"]["span"] = "this text is not in the document"
            record["summary"] = {
                "value": (
                    f"{c.expected['charging_party']} alleges {', '.join(c.expected['issues']).lower()} "
                    f"based on {', '.join(c.expected['bases']).lower()}."
                ),
                "page": 1,
                "span": None,
                "confidence": 0.5,
            }
            return json.dumps(record)
        return "{}"

    return respond


def find_span(field: str, value: object, pages: list[str]) -> str | None:
    """The line of page text that carries `value`, or None."""
    if value in (None, "", []):
        return None
    probe = value[0] if isinstance(value, list) else str(value)
    if field in ("earliest_date", "latest_date"):
        y, m, d = str(value).split("-")
        probe = f"{m}/{d}/{y}"
    if field == "continuing_action":
        probe = "CONTINUING ACTION"
    for p in pages:
        for line in p.splitlines():
            if probe.casefold() in line.casefold():
                return line.strip()
    return None
