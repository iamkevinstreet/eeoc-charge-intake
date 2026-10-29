########################################################################
#                  backend/eeoc_intake/api/reviews.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The reviews in progress: each extraction with    #
#                     its decisions, kept in memory, and the export.   #
########################################################################
"""Reviews in progress, kept in memory, and the record they export.

A review holds one extraction and a decision per field. It exports
only when every field is decided. The store keeps the newest
`[api] max_reviews` and drops the oldest: a prototype's memory, not a
database, which the README lists as unresolved.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Final

from kds.logs import get_logger

from eeoc_intake.core.extract import Extraction, response_due
from eeoc_intake.core.schema import FIELDS, Decision, Value

# Module constants
log = get_logger(__name__)
# log.debug("Sets the length of a review id, in hex digits")
ID_DIGITS: Final = 10
# log.debug("Sets the time stamp's precision")
TIMESPEC: Final = "seconds"
# log.debug("Names the field the response deadline is counted from")
NOTICE_FIELD: Final = "notice_date"
# log.debug("Names the review id key both answers carry")
REVIEW_ID: Final = "review_id"
# log.debug("Names the record key both answers carry")
RECORD: Final = "record"
# log.debug("Names the decisions key both answers carry")
DECISIONS: Final = "decisions"


# log.debug("Defines one review")
@dataclass
class Review:
    """One extraction under review and the decisions made so far.

    Attributes:
        review_id: The review's id, ten hex digits.
        source: Where the documents came from, a sample or an upload.
        demo: Whether the offline stand-in made the extraction.
        created_at: When the review began, in UTC.
        request_id: The request that made the extraction, for the logs.
        extraction: The extraction under review.
        decisions: Each decided field's decision.
    """

    # log.debug("Holds the id")
    review_id: str
    # log.debug("Holds the source")
    source: str
    # log.debug("Holds whether this is demo output")
    demo: bool
    # log.debug("Holds when it began")
    created_at: str
    # log.debug("Holds the request id")
    request_id: str
    # log.debug("Holds the extraction")
    extraction: Extraction
    # log.debug("Holds the decisions, by field")
    decisions: dict[str, Decision] = field(default_factory=dict)


# log.debug("Defines the store")
class ReviewStore:
    """The reviews of one process, the oldest dropped past the limit."""

    # log.debug("Defines the constructor")
    def __init__(self, limit: int) -> None:
        """Keep at most `limit` reviews."""
        # log.debug("Keeps the limit")
        self.limit = limit
        # log.debug("Starts the reviews, oldest first")
        self._reviews: OrderedDict[str, Review] = OrderedDict()
        # log.debug("Guards the reviews across request threads")
        self._lock = threading.Lock()

    # log.debug("Defines adding a review")
    def add(self, extraction: Extraction, *, source: str, demo: bool, request_id: str) -> Review:
        """Start a review of `extraction`; return it."""
        # log.debug("Builds the review with a random id")
        review = Review(
            review_id=uuid.uuid4().hex[:ID_DIGITS],
            source=source,
            demo=demo,
            created_at=datetime.now(UTC).isoformat(timespec=TIMESPEC),
            request_id=request_id,
            extraction=extraction,
        )
        # log.debug("Stores it, dropping the oldest past the limit")
        with self._lock:
            # log.debug("Adds it as the newest")
            self._reviews[review.review_id] = review
            # log.debug("Drops the oldest while over the limit")
            while len(self._reviews) > self.limit:
                # log.debug("Drops one")
                self._reviews.popitem(last=False)
        # log.debug("Returns the review")
        return review

    # log.debug("Defines finding a review")
    def get(self, review_id: str) -> Review | None:
        """Return the review, or None when there is no such review."""
        # log.debug("Returns it under the lock")
        with self._lock:
            # log.debug("Returns the review or None")
            return self._reviews.get(review_id)

    # log.debug("Defines recording a decision")
    def decide(self, review: Review, decision: Decision) -> int:
        """Record the decision; return how many fields are decided.

        Raises:
            ValueError: For a field the record does not have.
        """
        # log.debug("Refuses a field the record does not have")
        if decision.field not in FIELDS:
            # log.debug("Raises with the unknown field's name")
            msg = f"unknown field {decision.field}"
            # log.debug("Raises it")
            raise ValueError(msg)
        # log.debug("Records it, replacing any earlier decision on the field")
        with self._lock:
            # log.debug("Stores the decision")
            review.decisions[decision.field] = decision
            # log.debug("Returns the count")
            return len(review.decisions)


# log.debug("Defines what the review screen receives")
def payload(review: Review) -> dict[str, Any]:
    """Return the review as the review screen reads it."""
    # log.debug("Reads the extraction")
    ex = review.extraction
    # log.debug("Returns the review, the extraction and the decisions so far")
    return {
        REVIEW_ID: review.review_id,
        "source": review.source,
        "demo": review.demo,
        "created_at": review.created_at,
        "request_id": review.request_id,
        "model": ex.model,
        "cost_usd": ex.cost_usd,
        "latency_ms": ex.latency_ms,
        "fields": FIELDS,
        RECORD: ex.record.model_dump(),
        "raw": ex.raw.model_dump(),
        "removed": ex.removed,
        "pages": {"charge": ex.charge_pages, "notice": ex.notice_pages},
        DECISIONS: {f: d.model_dump() for f, d in review.decisions.items()},
        "decided": len(review.decisions),
        "total": len(FIELDS),
    }


# log.debug("Defines the fields still waiting for a decision")
def undecided(review: Review) -> list[str]:
    """Return the fields with no decision yet, in the record's order."""
    # log.debug("Returns them")
    return [f for f in FIELDS if f not in review.decisions]


# log.debug("Defines the exported record")
def exported(review: Review, *, response_days: int) -> dict[str, Any]:
    """Return the decided record and the response deadline.

    Accepted fields keep the extracted value, edited ones the reviewer's
    value, and rejected ones are empty. The caller checks that every
    field is decided first.
    """
    # log.debug("Applies each field's decision")
    record = {f: _decided_value(review, f) for f in FIELDS}
    # log.debug("Returns the record, its deadline and the decisions")
    return {
        REVIEW_ID: review.review_id,
        "exported_at": datetime.now(UTC).isoformat(timespec=TIMESPEC),
        RECORD: record,
        "response_due": _due(record.get(NOTICE_FIELD), response_days),
        DECISIONS: {f: d.action for f, d in review.decisions.items()},
    }


# log.debug("Defines one field's value after its decision")
def _decided_value(review: Review, name: str) -> Value:
    """Return the value the decision leaves the field with."""
    # log.debug("Reads the decision")
    decision = review.decisions[name]
    # log.debug("Empties a rejected field")
    if decision.action == "reject":
        # log.debug("Returns empty")
        return None
    # log.debug("Returns an edit's value, or the extracted value when accepted")
    return (
        decision.value
        if decision.action == "edit"
        else review.extraction.record.sourced(name).value
    )


# log.debug("Defines the deadline counted from the notice date")
def _due(notice: Value, days: int) -> str | None:
    """Return the response deadline, or None without a valid date."""
    # log.debug("Returns None when the notice date is not text")
    if not isinstance(notice, str):
        # log.debug("Returns None")
        return None
    # log.debug("Reads the date, which an edit may have left invalid")
    try:
        # log.debug("Returns the deadline as an ISO date")
        return response_due(date.fromisoformat(notice), days).isoformat()
    except ValueError:
        # log.debug("Returns None for a date that does not parse")
        return None
