"""The intake record. Every field carries the evidence it came from, or the reason it is empty."""

from __future__ import annotations

from pydantic import BaseModel, Field

FIELDS = [
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
]


class Sourced(BaseModel):
    value: str | list[str] | bool | None = None
    page: int | None = Field(default=None, description="1-based page the span was found on")
    span: str | None = Field(default=None, description="Exact text from the document that supports the value")
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str | None = Field(default=None, description="Why the value is empty, when it is")


class ChargeRecord(BaseModel):
    charge_number: Sourced = Sourced()
    charging_party: Sourced = Sourced()
    respondent: Sourced = Sourced()
    eeoc_office: Sourced = Sourced()
    bases: Sourced = Sourced()
    issues: Sourced = Sourced()
    earliest_date: Sourced = Sourced()
    latest_date: Sourced = Sourced()
    continuing_action: Sourced = Sourced()
    notice_date: Sourced = Sourced()
    summary: Sourced = Sourced()

    def values(self) -> dict:
        return {f: getattr(self, f).value for f in FIELDS}


class Decision(BaseModel):
    field: str
    action: str = Field(pattern="^(accept|edit|reject)$")
    value: str | list[str] | bool | None = None
