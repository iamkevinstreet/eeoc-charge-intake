########################################################################
#                                                                      #
#                backend/src/eeoc_intake/core/guard.py                 #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Finds the sentences of a charge or notice that give orders to an AI
model, such as a planted note telling it to record false values. They
change nothing in the extraction: the model is told the pages are data,
and the reviewer is shown each flagged sentence with its page, so a
value that came from one can be caught.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import re
from typing import Final, Literal

# Third-party
from kds.args import missing, required
from kds.logs import get_logger
from pydantic import BaseModel, ConfigDict

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
# log.debug("Lists patterns of text that gives orders to a model or a system")
PATTERNS: Final = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(ignore|disregard|forget|override)\b[^.]{0,40}"
        r"\b(instructions?|prompts?|rules|directions)\b",
        r"\b(note|instructions?|message)s? (to|for) (any |the )?"
        r"(ai|assistant|agent|model|llm|system|extractor)\b",
        r"\bsystem (note|message|prompt|instructions?)\b",
        r"\b(record|report|enter|set|write)\b[^.]{0,30}\b(charge number|charging party|"
        r"respondent|office|bases|issues|dates?)\b[^.]{0,20}\bas\b",
        r"\b(do not|don't) (mention|reveal|report) (this|these)\b",
        r"</?\s*(system|instructions?|prompt)\s*>",
    )
)
# log.debug("Splits a page's text into sentences")
SENTENCE: Final = re.compile(r"(?<=[.!?])\s+")
# log.debug("Sets how much of a flagged sentence is kept")
SHOWN_CHARS: Final = 300
# log.debug("Lists the documents a flagged sentence can come from")
Document = Literal["charge", "notice"]


########################################################################
#                                                                      #
#                           Injection check                            #
#                                                                      #
########################################################################
# log.debug("Defines one flagged sentence")
class Flagged(BaseModel):
    """A sentence that gives orders, and where it is."""

    # log.debug("Freezes it, since it is a finding")
    model_config = ConfigDict(frozen=True)

    # log.debug("Holds the document it is in")
    document: Document
    # log.debug("Holds its page, from 1")
    page: int
    # log.debug("Holds the sentence, cut to SHOWN_CHARS")
    text: str


# log.debug("Defines the check over both documents")
def flag_pages(
    charge_pages: list[str] | None = None, notice_pages: list[str] | None = None
) -> list[Flagged]:
    """Returns every sentence of either document that gives orders.

    Args:
        charge_pages: The charge's page texts, in order. Required.
        notice_pages: The notice's page texts, in order. Required.

    Returns:
        Each flagged sentence with its document and page, charge first,
        in page order.
    """
    # log.debug("Takes the charge pages, which the caller must give")
    charge_pages = required(charge_pages=charge_pages)
    # log.debug("Takes the notice pages, which the caller must give")
    notice_pages = required(notice_pages=notice_pages)
    # log.debug("Returns the charge's flags, then the notice's")
    return [*_flag("charge", charge_pages), *_flag("notice", notice_pages)]


# log.debug("Defines the check over one document")
def _flag(document: Document | None = None, pages: list[str] | None = None) -> list[Flagged]:
    """Returns the sentences of one document that give orders.

    A page's lines are joined first, since a sentence may wrap.

    Args:
        document: Which document the pages are. Required.
        pages: Its page texts, in order. Required.

    Returns:
        Each flagged sentence with its page.
    """
    # log.debug("Stops when the caller left out the document")
    if document is None:
        # log.debug("Raises the missing-argument error")
        raise missing(document=document)
    # log.debug("Takes the pages, which the caller must give")
    pages = required(pages=pages)
    # log.debug("Returns each sentence that matches a pattern, with its page")
    return [
        Flagged(document=document, page=number, text=sentence[:SHOWN_CHARS])
        for number, page in enumerate(pages, start=1)
        for sentence in SENTENCE.split(" ".join(page.split()))
        if any(pattern.search(sentence) for pattern in PATTERNS)
    ]
