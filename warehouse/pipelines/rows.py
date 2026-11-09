########################################################################
#                                                                      #
#                     warehouse/pipelines/rows.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

The raw contract: one Pydantic model per raw table, which dlt also
reads for the table's columns. A field a model does not name fails the
load instead of adding a column.

A review export is three tables: the export itself; every value of its
record and of what the model read, one row per field and list item;
and each field's decision, with whether the quote check emptied it.
Every row carries the export it came from and when it was loaded.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from datetime import date, datetime
from typing import Final, Literal

# Third-party
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
# log.debug("Sets every row's model settings: frozen, and no field it does not name")
STRICT: Final = ConfigDict(frozen=True, extra="forbid")
# log.debug("Types the two versions of a record an export holds")
Version = Literal["record", "extracted"]
# log.debug("Types a reviewer's decision on one field")
Action = Literal["accept", "edit", "reject"]


########################################################################
#                                                                      #
#                               Raw rows                               #
#                                                                      #
########################################################################
# log.debug("Defines a row of the EEOC's receipts table")
class ReceiptRow(BaseModel):
    """Charges the EEOC received in one fiscal year citing one basis."""

    # log.debug("Freezes the row and refuses any field it does not name")
    model_config = STRICT

    # log.debug("Holds the EEOC's name for the table, E1a")
    table_id: str
    # log.debug("Holds the basis or statute, as the EEOC labels it")
    basis: str
    # log.debug("Holds the federal fiscal year, October to September")
    fiscal_year: int
    # log.debug("Holds how many charges cited the basis that year")
    receipts: int
    # log.debug("Holds where the file came from")
    source_url: str
    # log.debug("Holds the SHA-256 of the file, so a revision shows")
    source_sha256: str
    # log.debug("Holds when the load that wrote the row started")
    loaded_at: datetime


# log.debug("Defines a row per review export")
class ExportRow(BaseModel):
    """One export of a finished review, as the service wrote it."""

    # log.debug("Freezes the row and refuses any field it does not name")
    model_config = STRICT

    # log.debug("Holds the export's key: its review and when it was exported")
    export_id: str
    # log.debug("Holds the review the export is of")
    review_id: str
    # log.debug("Holds the contract's name and version")
    contract: str
    # log.debug("Holds where the documents came from: sample: or upload:")
    source: str
    # log.debug("Holds whether the service answered in demo mode")
    demo: bool
    # log.debug("Holds when the review began")
    started_at: datetime
    # log.debug("Holds when the review was exported")
    exported_at: datetime
    # log.debug("Holds when the respondent's position statement is due, if it can be known")
    response_due: date | None
    # log.debug("Holds the file the export was read from")
    file: str
    # log.debug("Holds when the load that wrote the row started")
    loaded_at: datetime


# log.debug("Defines a row per value of an export's record or reading")
class ValueRow(BaseModel):
    """One value of one field, or one item of a list field."""

    # log.debug("Freezes the row and refuses any field it does not name")
    model_config = STRICT

    # log.debug("Holds the export the value belongs to")
    export_id: str
    # log.debug("Holds the review the export is of")
    review_id: str
    # log.debug("Holds the version: the record after review, or what the model read")
    version: Version
    # log.debug("Holds the field's name")
    field: str
    # log.debug("Holds the item's place in a list, 0 for a single value")
    position: int
    # log.debug("Holds the value as text: true and false for a yes or no")
    value: str
    # log.debug("Holds when the load that wrote the row started")
    loaded_at: datetime


# log.debug("Defines a row per field's decision")
class DecisionRow(BaseModel):
    """A reviewer's decision on one field of one export."""

    # log.debug("Freezes the row and refuses any field it does not name")
    model_config = STRICT

    # log.debug("Holds the export the decision belongs to")
    export_id: str
    # log.debug("Holds the review the export is of")
    review_id: str
    # log.debug("Holds the field's name")
    field: str
    # log.debug("Holds the decision: accept, edit or reject")
    decision: Action
    # log.debug("Holds whether the quote check emptied the field before review")
    removed: bool
    # log.debug("Holds when the load that wrote the row started")
    loaded_at: datetime
