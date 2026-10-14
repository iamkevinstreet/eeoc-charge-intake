"""Review service: upload a pair of PDFs, get a record with evidence, decide each field, export only when done.

uvicorn eeoc_intake.api:app --reload
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from kds.llm.adapter import get_adapter
from kds.logs import new_request_id

from eeoc_intake.extract import extract
from eeoc_intake.schema import FIELDS, ChargeRecord, Decision

app = FastAPI(title="EEOC charge intake", version="0.1.0")
_reviews: dict[str, dict] = {}  # prototype store; a pilot would use a database


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/extract")
async def extract_endpoint(charge: UploadFile, notice: UploadFile) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / "charge.pdf"
        n = Path(tmp) / "notice.pdf"
        c.write_bytes(await charge.read())
        n.write_bytes(await notice.read())
        with new_request_id() as rid:
            record = extract(get_adapter(), c, n)
    review_id = uuid.uuid4().hex[:10]
    _reviews[review_id] = {"record": record, "decisions": {}, "request_id": rid}
    return {"review_id": review_id, "record": record.model_dump()}


@app.post("/reviews/{review_id}/decisions")
def decide(review_id: str, decision: Decision) -> dict:
    review = _reviews.get(review_id)
    if review is None:
        raise HTTPException(404, "unknown review")
    if decision.field not in FIELDS:
        raise HTTPException(400, f"unknown field {decision.field}")
    review["decisions"][decision.field] = decision
    return {"decided": len(review["decisions"]), "total": len(FIELDS)}


@app.get("/reviews/{review_id}/export")
def export(review_id: str) -> dict:
    review = _reviews.get(review_id)
    if review is None:
        raise HTTPException(404, "unknown review")
    missing = [f for f in FIELDS if f not in review["decisions"]]
    if missing:
        raise HTTPException(409, f"undecided fields: {missing}")
    record: ChargeRecord = review["record"]
    out = {}
    for f in FIELDS:
        d: Decision = review["decisions"][f]
        if d.action == "reject":
            out[f] = None
        elif d.action == "edit":
            out[f] = d.value
        else:
            out[f] = getattr(record, f).value
    return {"review_id": review_id, "record": out}
