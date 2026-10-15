"""Review service: extract a record with evidence, decide each field, export only when every field is decided.

    uvicorn eeoc_intake.api:app --reload

The API lives under /api. When the review screen has been built (`npm run build` in ui/), the service serves
it at /. With LLM_PROVIDER=fake the service runs in demo mode: it can only extract the generated sample
documents, and it answers from their ground truth rather than from a model. The response says so.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from kds.evals.case import EvalCase, load_cases
from kds.llm.adapter import ModelAdapter, get_adapter
from kds.llm.fake import FakeProvider
from kds.logs import new_request_id
from kds.settings import get_settings

from eeoc_intake.extract import Extraction, extract, response_due
from eeoc_intake.fake import gold_responder
from eeoc_intake.schema import FIELDS, Decision

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = Path(os.environ.get("EEOC_SAMPLES_DIR", REPO_ROOT / "eeoc_intake" / "data" / "generated"))
RESULTS_DIR = Path(os.environ.get("EEOC_RESULTS_DIR", REPO_ROOT / "eeoc_intake" / "evals" / "results"))
UI_DIST = REPO_ROOT / "ui" / "dist"

app = FastAPI(title="EEOC charge intake", version="0.2.0")
api = APIRouter(prefix="/api")
_reviews: dict[str, dict] = {}  # prototype store; a pilot would use a database


def demo_mode() -> bool:
    return get_settings().llm_provider == "fake"


def _resolve(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    for base in (Path.cwd(), REPO_ROOT):
        if (base / path).exists():
            return base / path
    return path


@lru_cache(maxsize=1)
def sample_cases() -> list[EvalCase]:
    cases_file = SAMPLES_DIR / "cases.jsonl"
    if not cases_file.exists():
        return []
    cases = load_cases(cases_file)
    for c in cases:
        c.input = {k: str(_resolve(v)) for k, v in c.input.items()}
    return cases


def _adapter() -> ModelAdapter:
    if demo_mode():
        return ModelAdapter(FakeProvider(responder=gold_responder(sample_cases())), model="fake-model")
    return get_adapter()


def _new_review(extraction: Extraction, source: str, request_id: str) -> dict:
    review_id = uuid.uuid4().hex[:10]
    _reviews[review_id] = {
        "review_id": review_id,
        "source": source,
        "demo": demo_mode(),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "request_id": request_id,
        "extraction": extraction,
        "decisions": {},
    }
    return _review_payload(_reviews[review_id])


def _review_payload(review: dict) -> dict:
    ex: Extraction = review["extraction"]
    return {
        "review_id": review["review_id"],
        "source": review["source"],
        "demo": review["demo"],
        "created_at": review["created_at"],
        "request_id": review["request_id"],
        "model": ex.model,
        "cost_usd": ex.cost_usd,
        "latency_ms": ex.latency_ms,
        "fields": FIELDS,
        "record": ex.record.model_dump(),
        "raw": ex.raw.model_dump(),
        "removed": ex.removed,
        "pages": {"charge": ex.charge_pages, "notice": ex.notice_pages},
        "decisions": {f: d.model_dump() for f, d in review["decisions"].items()},
        "decided": len(review["decisions"]),
        "total": len(FIELDS),
    }


@api.get("/health")
def health() -> dict:
    s = get_settings()
    return {"ok": True, "provider": s.llm_provider, "model": s.llm_model, "demo": demo_mode()}


@api.get("/samples")
def samples() -> list[dict]:
    return [
        {
            "id": c.id,
            "tags": c.tags,
            "charge_pdf": Path(c.input["charge_pdf"]).name,
            "notice_pdf": Path(c.input["notice_pdf"]).name,
        }
        for c in sample_cases()
    ]


@api.post("/extract")
async def extract_upload(charge: UploadFile, notice: UploadFile) -> dict:
    if demo_mode():
        raise HTTPException(
            409,
            "Demo mode (LLM_PROVIDER=fake) answers only for the generated samples. "
            "Set a real provider to extract uploaded documents.",
        )
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / "charge.pdf"
        n = Path(tmp) / "notice.pdf"
        c.write_bytes(await charge.read())
        n.write_bytes(await notice.read())
        with new_request_id() as rid:
            extraction = extract(_adapter(), c, n)
    return _new_review(extraction, source=f"upload:{charge.filename}", request_id=rid)


@api.post("/extract/sample/{sample_id}")
def extract_sample(sample_id: str) -> dict:
    case = next((c for c in sample_cases() if c.id == sample_id), None)
    if case is None:
        raise HTTPException(404, f"unknown sample {sample_id}")
    with new_request_id() as rid:
        extraction = extract(_adapter(), case.input["charge_pdf"], case.input["notice_pdf"])
    return _new_review(extraction, source=f"sample:{sample_id}", request_id=rid)


@api.get("/reviews/{review_id}")
def get_review(review_id: str) -> dict:
    review = _reviews.get(review_id)
    if review is None:
        raise HTTPException(404, "unknown review")
    return _review_payload(review)


@api.post("/reviews/{review_id}/decisions")
def decide(review_id: str, decision: Decision) -> dict:
    review = _reviews.get(review_id)
    if review is None:
        raise HTTPException(404, "unknown review")
    if decision.field not in FIELDS:
        raise HTTPException(400, f"unknown field {decision.field}")
    review["decisions"][decision.field] = decision
    return {"decided": len(review["decisions"]), "total": len(FIELDS)}


@api.get("/reviews/{review_id}/export")
def export(review_id: str) -> dict:
    review = _reviews.get(review_id)
    if review is None:
        raise HTTPException(404, "unknown review")
    missing = [f for f in FIELDS if f not in review["decisions"]]
    if missing:
        raise HTTPException(409, f"undecided fields: {missing}")
    ex: Extraction = review["extraction"]
    out: dict = {}
    for f in FIELDS:
        d: Decision = review["decisions"][f]
        if d.action == "reject":
            out[f] = None
        elif d.action == "edit":
            out[f] = d.value
        else:
            out[f] = getattr(ex.record, f).value
    due = None
    if isinstance(out.get("notice_date"), str):
        try:
            due = response_due(date.fromisoformat(out["notice_date"])).isoformat()
        except ValueError:
            due = None
    return {
        "review_id": review_id,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "record": out,
        "response_due": due,
        "decisions": {f: d.action for f, d in review["decisions"].items()},
    }


@api.get("/evals/latest")
def latest_eval() -> dict:
    runs = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime) if RESULTS_DIR.exists() else []
    if not runs:
        raise HTTPException(404, "no evaluation results yet")
    return json.loads(runs[-1].read_text(encoding="utf-8"))


app.include_router(api)

if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")
else:

    @app.get("/")
    def index() -> dict:
        return {
            "service": "EEOC charge intake",
            "api": "/api",
            "docs": "/docs",
            "ui": "build ui/ to serve it here",
        }
