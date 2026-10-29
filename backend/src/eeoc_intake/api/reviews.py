########################################################################
#                backend/src/eeoc_intake/api/reviews.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Keeps the reviews in progress, each an extraction with the decisions
made on its fields, and builds the record a finished review exports.
A review exports only when every field is decided. The store keeps the
newest `[api] max_reviews` in memory and drops the oldest: it is not a
database, which the README lists as unresolved.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Final

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.config import SETTINGS
from eeoc_intake.core.extract import Extraction, response_due
from eeoc_intake.core.schema import FIELDS, Decision, Value

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the field the response deadline is counted from, from the config")
NOTICE_FIELD: Final = SETTINGS.record_notice_field

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the length of a review id, in hex digits")
ID_DIGITS: Final = 10
# log.debug("Sets the time stamp's precision")
TIMESPEC: Final = "seconds"
# log.debug("Names the review id key both answers carry")
REVIEW_ID: Final = "review_id"
# log.debug("Names the record key both answers carry")
RECORD: Final = "record"
# log.debug("Names the decisions key both answers carry")
DECISIONS: Final = "decisions"


########################################################################
#                         Reviews in progress                          #
########################################################################
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
    def __init__(self, limit: int | None = None) -> None:
        """Keeps at most `limit` reviews.

        Args:
            limit: The most reviews kept; the oldest go first. Required.
        """
        # log.debug("Takes the limit, which the caller must give")
        limit = required(limit=limit)
        # log.debug("Keeps the limit")
        self.limit = limit
        # log.debug("Starts the reviews, oldest first")
        self._reviews: OrderedDict[str, Review] = OrderedDict()
        # log.debug("Guards the reviews across request threads")
        self._lock = threading.Lock()

    # log.debug("Defines adding a review")
    def add(
        self,
        extraction: Extraction | None = None,
        *,
        source: str | None = None,
        demo: bool | None = None,
        request_id: str | None = None,
    ) -> Review:
        """Starts a review of an extraction and stores it.

        Args:
            extraction: The extraction to review. Required.
            source: Where the documents came from: sample:<id> or
                upload:<name>. Required.
            demo: Whether the offline stand-in made the extraction.
                Required.
            request_id: The id of the request that made the extraction.
                Required.

        Returns:
            The new review, with no decisions yet.
        """
        # log.debug("Takes the extraction, which the caller must give")
        extraction = required(extraction=extraction)
        # log.debug("Takes the source, which the caller must give")
        source = required(source=source)
        # log.debug("Takes whether this is demo output, which the caller must give")
        demo = required(demo=demo)
        # log.debug("Takes the request id, which the caller must give")
        request_id = required(request_id=request_id)
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
    def get(self, review_id: str | None = None) -> Review | None:
        """Returns the review, or None when there is no such review.

        Args:
            review_id: The review's id. Required.

        Returns:
            The review, or None when the store holds none with the id.
        """
        # log.debug("Takes the review id, which the caller must give")
        review_id = required(review_id=review_id)
        # log.debug("Returns it under the lock")
        with self._lock:
            # log.debug("Returns the review or None")
            return self._reviews.get(review_id)

    # log.debug("Defines recording a decision")
    def decide(self, review: Review | None = None, decision: Decision | None = None) -> int:
        """Records a decision on one field, replacing any earlier one.

        Args:
            review: The review the decision is for. Required.
            decision: The reviewer's decision on one field. Required.

        Returns:
            How many of the review's fields now have a decision.

        Raises:
            ValueError: For a field the record does not have.
        """
        # log.debug("Takes the review, which the caller must give")
        review = required(review=review)
        # log.debug("Takes the decision, which the caller must give")
        decision = required(decision=decision)
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
def payload(review: Review | None = None) -> dict[str, Any]:
    """Returns the review as the review screen reads it.

    Args:
        review: The review to show. Required.

    Returns:
        The review's id, source and model, the extraction with its
        evidence and page text, and the decisions so far.
    """
    # log.debug("Takes the review, which the caller must give")
    review = required(review=review)
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
def undecided(review: Review | None = None) -> list[str]:
    """Returns the fields with no decision yet, in the record's order.

    Args:
        review: The review to check. Required.

    Returns:
        The names of the fields still waiting for a decision.
    """
    # log.debug("Takes the review, which the caller must give")
    review = required(review=review)
    # log.debug("Returns them")
    return [f for f in FIELDS if f not in review.decisions]


# log.debug("Defines the exported record")
def exported(review: Review | None = None, *, response_days: int | None = None) -> dict[str, Any]:
    """Returns the decided record and the response deadline.

    Accepted fields keep the extracted value, edited ones the reviewer's
    value, and rejected ones are empty. The caller checks that every
    field is decided first.

    Args:
        review: The review, with every field decided. Required.
        response_days: The days after the notice date a position
            statement is due. Required.

    Returns:
        The record after the decisions, when it was exported, the
        response deadline (None without a valid notice date) and each
        field's decision.
    """
    # log.debug("Takes the review, which the caller must give")
    review = required(review=review)
    # log.debug("Takes the response days, which the caller must give")
    response_days = required(response_days=response_days)
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
def _decided_value(review: Review | None = None, name: str | None = None) -> Value:
    """Returns the value the decision leaves the field with.

    Args:
        review: The review that holds the decision. Required.
        name: The field's name. Required.

    Returns:
        The extracted value when accepted, the reviewer's value when
        edited, and None when rejected.
    """
    # log.debug("Takes the review, which the caller must give")
    review = required(review=review)
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
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
def _due(notice: Value = None, days: int | None = None) -> str | None:
    """Returns the response deadline, or None without a valid date.

    Args:
        notice: The notice date as the record holds it; None, or
            anything but an ISO date, gives no deadline.
        days: The days the respondent has to answer. Required.

    Returns:
        The deadline as an ISO date, or None.
    """
    # log.debug("Takes the days, which the caller must give")
    days = required(days=days)
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
