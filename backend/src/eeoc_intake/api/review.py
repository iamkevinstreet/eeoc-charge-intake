########################################################################
#                                                                      #
#                backend/src/eeoc_intake/api/review.py                 #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-08
Last modified on:  2026-11-08

What a review is, whichever store keeps it: the Review itself, the
Store protocol the memory and Postgres stores both follow, and how a
review starts and how its times are written.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Protocol

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from eeoc_intake.core.extract import Extraction
from eeoc_intake.core.schema import Decision

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
# log.debug("Sets the length of a review id, in hex digits")
ID_DIGITS: Final = 10
# log.debug("Sets the time stamp's precision")
TIMESPEC: Final = "seconds"


########################################################################
#                                                                      #
#                                Review                                #
#                                                                      #
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
        exports: What each export returned, in the memory store.
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
    # log.debug("Holds what each export returned, oldest first")
    exports: list[dict[str, Any]] = field(default_factory=list)


# log.debug("Defines what every store can do: memory here, Postgres in api/store.py")
class Store(Protocol):
    """Starts, finds and decides reviews, and records their exports."""

    # log.debug("Declares the start of a review")
    def add(
        self,
        extraction: Extraction | None = None,
        *,
        source: str | None = None,
        demo: bool | None = None,
        request_id: str | None = None,
    ) -> Review:
        """Starts a review of an extraction and keeps it.

        Args:
            extraction: The extraction to review. Required.
            source: Where the documents came from. Required.
            demo: Whether the offline stand-in made the extraction.
                Required.
            request_id: The request that made the extraction. Required.

        Returns:
            The new review.
        """

    # log.debug("Declares the lookup of a review")
    def get(self, review_id: str | None = None) -> Review | None:
        """Returns the review, or None.

        Args:
            review_id: The review's id. Required.

        Returns:
            The review, or None when there is no such review.
        """

    # log.debug("Declares the record of a decision")
    def decide(self, review: Review | None = None, decision: Decision | None = None) -> int:
        """Records a decision on one field, replacing any earlier one.

        Args:
            review: The review the decision is for. Required.
            decision: The reviewer's decision on one field. Required.

        Returns:
            How many of the review's fields now have a decision.
        """

    # log.debug("Declares the record of an export")
    def record_export(
        self, review: Review | None = None, export: dict[str, Any] | None = None
    ) -> None:
        """Records what an export returned.

        Args:
            review: The review exported. Required.
            export: What the export returned. Required.
        """


# log.debug("Defines the start of a review, the same in every store")
def start_review(
    extraction: Extraction | None = None,
    *,
    source: str | None = None,
    demo: bool | None = None,
    request_id: str | None = None,
) -> Review:
    """Returns a new review of the extraction, with a random id.

    Args:
        extraction: The extraction to review. Required.
        source: Where the documents came from: sample:<id> or
            upload:<name>. Required.
        demo: Whether the offline stand-in made the extraction.
            Required.
        request_id: The id of the request that made the extraction.
            Required.

    Returns:
        The review, with no decisions yet, begun now.
    """
    # log.debug("Takes the extraction, which the caller must give")
    extraction = required(extraction=extraction)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Takes whether this is demo output, which the caller must give")
    demo = required(demo=demo)
    # log.debug("Takes the request id, which the caller must give")
    request_id = required(request_id=request_id)
    # log.debug("Returns the review with a random id, begun now")
    return Review(
        review_id=uuid.uuid4().hex[:ID_DIGITS],
        source=source,
        demo=demo,
        created_at=stamp(datetime.now(UTC)),
        request_id=request_id,
        extraction=extraction,
    )


# log.debug("Defines how a time is written in reviews and exports")
def stamp(moment: datetime | None = None) -> str:
    """Returns the time in UTC, to the second, in ISO 8601.

    Args:
        moment: A time with its zone. Required.

    Returns:
        The time, such as 2026-11-08T05:00:00+00:00.
    """
    # log.debug("Takes the time, which the caller must give")
    moment = required(moment=moment)
    # log.debug("Returns it in UTC, to the second")
    return moment.astimezone(UTC).isoformat(timespec=TIMESPEC)
