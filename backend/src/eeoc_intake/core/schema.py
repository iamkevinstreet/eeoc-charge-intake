########################################################################
#                backend/src/eeoc_intake/core/schema.py                #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The intake record: eleven fields, each with the  #
#                     evidence it came from or the reason it is empty. #
########################################################################
"""The intake record and a reviewer's decision on one field."""

from __future__ import annotations

from typing import Final, Literal

from kds.logs import get_logger
from pydantic import BaseModel, ConfigDict, Field

# Module constants
log = get_logger(__name__)
# log.debug("Lists the record's fields in the order they are shown")
FIELDS: Final = (
    "charge_number",
    "charging_party",
    "respondent",
    "eeoc_office",
    "bases",
    "issues",
    "earliest_date",
    "latest_date",
    "continuing_action",
    "notice_date",
    "summary",
)
# log.debug("Lists the fields scored against the known answers; a summary is a paraphrase")
SCORED_FIELDS: Final = tuple(f for f in FIELDS if f != "summary")
# log.debug("Lists the values a field may hold")
Value = str | list[str] | bool | None
# log.debug("Lists what a reviewer may do with a field")
Action = Literal["accept", "edit", "reject"]


# log.debug("Defines one field with its evidence")
class Sourced(BaseModel):
    """A value, the page and text that support it, and how sure."""

    # log.debug("Holds the extracted value, or None when the document lacks it")
    value: Value = None
    # log.debug("Holds the one-based page the quote was found on")
    page: int | None = Field(default=None, description="1-based page the span was found on")
    # log.debug("Holds the exact text from the document that supports the value")
    span: str | None = Field(
        default=None, description="Exact text from the document that supports the value"
    )
    # log.debug("Holds the model's own estimate that the value is right")
    confidence: float = Field(default=0.0, ge=0, le=1)
    # log.debug("Holds why the value is empty, when it is")
    reason: str | None = Field(default=None, description="Why the value is empty, when it is")


# log.debug("Defines the record")
class ChargeRecord(BaseModel):
    """The eleven fields of one charge and its notice."""

    # log.debug("Holds the charge number")
    charge_number: Sourced = Sourced()
    # log.debug("Holds the charging party")
    charging_party: Sourced = Sourced()
    # log.debug("Holds the respondent, or a list when there are two")
    respondent: Sourced = Sourced()
    # log.debug("Holds the EEOC office")
    eeoc_office: Sourced = Sourced()
    # log.debug("Holds the protected bases")
    bases: Sourced = Sourced()
    # log.debug("Holds the employment actions the particulars describe")
    issues: Sourced = Sourced()
    # log.debug("Holds the earliest date of harm")
    earliest_date: Sourced = Sourced()
    # log.debug("Holds the latest date of harm")
    latest_date: Sourced = Sourced()
    # log.debug("Holds whether the form marks a continuing action")
    continuing_action: Sourced = Sourced()
    # log.debug("Holds the notice date, from the notice letter")
    notice_date: Sourced = Sourced()
    # log.debug("Holds a summary of the particulars in at most three sentences")
    summary: Sourced = Sourced()

    # log.debug("Defines the plain values of every field")
    def values(self) -> dict[str, Value]:
        """Return each field's value, without its evidence."""
        # log.debug("Returns the values by field name")
        return {f: self.sourced(f).value for f in FIELDS}

    # log.debug("Defines the lookup of one field by name")
    def sourced(self, name: str) -> Sourced:
        """Return the named field.

        Raises:
            KeyError: For a name that is not one of the fields.
        """
        # log.debug("Reads the attribute of that name")
        value = getattr(self, name, None)
        # log.debug("Refuses a name that is not a field")
        if not isinstance(value, Sourced):
            # log.debug("Raises for the unknown field")
            raise KeyError(name)
        # log.debug("Returns the field")
        return value


# log.debug("Defines a reviewer's decision on one field")
class Decision(BaseModel):
    """Accept, edit (with the new value) or reject one field."""

    # log.debug("Refuses fields the decision does not declare")
    model_config = ConfigDict(extra="forbid")

    # log.debug("Holds the field decided")
    field: str
    # log.debug("Holds what the reviewer did")
    action: Action
    # log.debug("Holds the edited value, for an edit")
    value: Value = None
