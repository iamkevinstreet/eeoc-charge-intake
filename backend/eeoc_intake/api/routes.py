########################################################################
#                  backend/eeoc_intake/api/routes.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The review routes: samples, extraction, one      #
#                     decision per field, export, the latest results.  #
########################################################################
"""The review service's routes, all under /api/v1.

- GET /health: provider, model and demo mode
- GET /samples: the generated documents a reviewer may open
- POST /extract: a charge PDF and a notice PDF (real models only)
- POST /extract/sample/{id}: one of the generated samples
- GET /reviews/{id}, POST /reviews/{id}/decisions: review a record
- GET /reviews/{id}/export: the record, once every field is decided
- GET /evals/latest: the newest evaluation run

In demo mode (the fake provider) the offline stand-in answers for the
generated samples only, and every response says so.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi import Path as PathParam
from kds.evals.case import EvalCase
from kds.llm.errors import BudgetExceededError, StructuredOutputError, is_transient
from kds.logs import current_request_id, get_logger, log_event

from eeoc_intake import __version__
from eeoc_intake.api.reviews import Review, exported, payload, undecided
from eeoc_intake.api.state import PREFIX, Services, services
from eeoc_intake.core.extract import Extraction, UnreadableDocumentError, extract
from eeoc_intake.core.schema import FIELDS, Decision

# Module constants
log = get_logger(__name__)
# log.debug("Builds the router every route hangs from")
router = APIRouter(prefix=PREFIX)
# log.debug("Sets the pattern of a sample id")
SAMPLE_ID: Final = r"^charge-\d{3,6}$"
# log.debug("Sets the pattern of a review id")
REVIEW_ID: Final = r"^[0-9a-f]{10}$"
# log.debug("Sets the first bytes of every PDF")
PDF_MAGIC: Final = b"%PDF-"
# log.debug("Sets the text encoding of the results files")
ENCODING: Final = "utf-8"
# log.debug("Sets the reply when a review does not exist")
NO_REVIEW: Final = "no such review"
# log.debug("Sets the most characters of an uploaded file's name kept")
NAME_CHARS: Final = 120
# log.debug("Sets the seconds a client should wait after the limit")
RETRY_AFTER: Final = "60"
# log.debug("Names the file an uploaded charge is saved as")
CHARGE_FILE: Final = "charge.pdf"
# log.debug("Names the input that holds the charge's path")
CHARGE_PDF: Final = "charge_pdf"
# log.debug("Names the input that holds the notice's path")
NOTICE_PDF: Final = "notice_pdf"
# log.debug("Types the services every route depends on")
Svc = Annotated[Services, Depends(services)]
# log.debug("Types a review id in a path")
ReviewId = Annotated[str, PathParam(pattern=REVIEW_ID)]


# log.debug("Defines the health check")
@router.get("/health")
def health(svc: Svc) -> dict[str, Any]:
    """Report the version, provider, model, and whether it is a demo."""
    # log.debug("Returns the report")
    return {
        "ok": True,
        "version": __version__,
        "provider": svc.settings.llm_provider,
        "model": svc.settings.llm_model,
        "demo": svc.demo,
    }


# log.debug("Defines the list of samples")
@router.get("/samples")
def samples(svc: Svc) -> list[dict[str, Any]]:
    """Return the generated documents, by id, kind and file name."""
    # log.debug("Returns each sample without its folder")
    return [
        {
            "id": s.id,
            "tags": s.tags,
            CHARGE_PDF: Path(s.input[CHARGE_PDF]).name,
            NOTICE_PDF: Path(s.input[NOTICE_PDF]).name,
        }
        for s in svc.samples.all()
    ]


# log.debug("Defines extraction from uploaded PDFs")
@router.post("/extract")
def extract_upload(
    charge: UploadFile, notice: UploadFile, request: Request, svc: Svc
) -> dict[str, Any]:
    """Extract an uploaded charge and notice and start their review.

    Raises:
        HTTPException: 409 in demo mode, 429 past the limit, 413 for a
            file over the limit, 415 for a file that is not a PDF.
    """
    # log.debug("Refuses uploads in demo mode, which knows only the samples")
    if svc.demo:
        # log.debug("Explains how to extract real documents")
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Demo mode (LLM_PROVIDER=fake) answers only for the generated samples. "
            "Set a real provider to extract uploaded documents.",
        )
    # log.debug("Refuses a client past its limit")
    _limit(svc, request)
    # log.debug("Reads both files within the size limit, checking each is a PDF")
    files = [_pdf(f, svc.settings.api_max_upload_bytes) for f in (charge, notice)]
    # log.debug("Writes them to a folder that is deleted afterwards")
    with tempfile.TemporaryDirectory() as tmp:
        # log.debug("Names the two files; the uploaded names are never used as paths")
        paths = [Path(tmp) / CHARGE_FILE, Path(tmp) / "notice.pdf"]
        # log.debug("Writes each file")
        for path, data in zip(paths, files, strict=True):
            # log.debug("Writes one")
            path.write_bytes(data)
        # log.debug("Extracts them")
        ex = _extract(svc, *paths)
    # log.debug("Starts the review and returns it")
    return payload(_start(svc, ex, source=f"upload:{_name(charge)}"))


# log.debug("Defines extraction from a generated sample")
@router.post("/extract/sample/{sample_id}")
def extract_sample(
    sample_id: Annotated[str, PathParam(pattern=SAMPLE_ID)], request: Request, svc: Svc
) -> dict[str, Any]:
    """Extract one generated sample and start its review.

    Raises:
        HTTPException: 404 for an unknown sample, 429 past the limit.
    """
    # log.debug("Finds the sample")
    case: EvalCase | None = svc.samples.get(sample_id)
    # log.debug("Answers 404 for a sample that does not exist")
    if case is None:
        # log.debug("Says which")
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no sample {sample_id}")
    # log.debug("Counts a real model's extraction against the client's limit")
    if not svc.demo:
        # log.debug("Refuses a client past its limit")
        _limit(svc, request)
    # log.debug("Extracts the sample's two documents")
    ex = _extract(svc, case.input[CHARGE_PDF], case.input[NOTICE_PDF])
    # log.debug("Starts the review and returns it")
    return payload(_start(svc, ex, source=f"sample:{sample_id}"))


# log.debug("Defines reading a review")
@router.get("/reviews/{review_id}")
def get_review(review_id: ReviewId, svc: Svc) -> dict[str, Any]:
    """Return the review with its decisions so far."""
    # log.debug("Returns the review")
    return payload(_review(svc, review_id))


# log.debug("Defines recording a decision")
@router.post("/reviews/{review_id}/decisions")
def decide(review_id: ReviewId, decision: Decision, svc: Svc) -> dict[str, int]:
    """Record a decision on one field; return the progress.

    Raises:
        HTTPException: 404 for an unknown review, 400 for an unknown
            field.
    """
    # log.debug("Finds the review")
    review = _review(svc, review_id)
    # log.debug("Records the decision")
    try:
        # log.debug("Stores it and counts the decided fields")
        decided = svc.reviews.decide(review, decision)
    except ValueError as error:
        # log.debug("Answers 400 for a field the record does not have")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    # log.debug("Returns the progress")
    return {"decided": decided, "total": len(FIELDS)}


# log.debug("Defines the export")
@router.get("/reviews/{review_id}/export")
def export(review_id: ReviewId, svc: Svc) -> dict[str, Any]:
    """Return the decided record, once every field is decided.

    Raises:
        HTTPException: 404 for an unknown review, 409 while any field
            is undecided.
    """
    # log.debug("Finds the review")
    review = _review(svc, review_id)
    # log.debug("Lists the fields still waiting for a decision")
    missing = undecided(review)
    # log.debug("Refuses to export while any field is undecided")
    if missing:
        # log.debug("Names them")
        raise HTTPException(status.HTTP_409_CONFLICT, f"undecided fields: {missing}")
    # log.debug("Logs the export, which ends the review")
    log_event(log, "review.exported", review_id=review_id)
    # log.debug("Returns the record")
    return exported(review, response_days=svc.settings.extract_response_days)


# log.debug("Defines the latest evaluation run")
@router.get("/evals/latest")
def latest_eval(svc: Svc) -> dict[str, Any]:
    """Return the newest live run, or the newest smoke run without one.

    Raises:
        HTTPException: 404 when there are no results yet.
    """
    # log.debug("Looks in the live results first, then the smoke results")
    for folder in (svc.settings.data_results, svc.settings.data_smoke):
        # log.debug("Reads the folder's runs")
        runs = _runs(folder)
        # log.debug("Returns the newest run when the folder has any")
        if runs:
            # log.debug("Returns it")
            return max(runs, key=lambda r: str(r["started_at"]))
    # log.debug("Answers 404 when there are no results")
    raise HTTPException(status.HTTP_404_NOT_FOUND, "no evaluation results yet")


# log.debug("Defines the per-client limit")
def _limit(svc: Services, request: Request) -> None:
    """Raise 429 once this client has used this minute's extractions."""
    # log.debug("Identifies the client by its address; the service is local")
    client = request.client.host if request.client else "unknown"
    # log.debug("Refuses past the limit")
    if not svc.limiter.allow(client):
        # log.debug("Raises 429 with a retry hint")
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too many extractions this minute; try again shortly",
            {"Retry-After": RETRY_AFTER},
        )


# log.debug("Defines reading one upload")
def _pdf(upload: UploadFile, limit: int) -> bytes:
    """Return the file's bytes, at most `limit`, checked to be a PDF.

    Raises:
        HTTPException: 413 over the limit, 415 for a file not a PDF.
    """
    # log.debug("Reads one byte past the limit, to tell when it is exceeded")
    data = upload.file.read(limit + 1)
    # log.debug("Refuses a file over the limit")
    if len(data) > limit:
        # log.debug("Raises 413")
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "a file is over the size limit")
    # log.debug("Refuses a file that does not start like a PDF")
    if not data.startswith(PDF_MAGIC):
        # log.debug("Raises 415")
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "both files must be PDFs")
    # log.debug("Returns the bytes")
    return data


# log.debug("Defines one extraction, with each failure as a clear reply")
def _extract(svc: Services, charge: Path | str, notice: Path | str) -> Extraction:
    """Extract, turning each known failure into an HTTP error.

    Raises:
        HTTPException: 422 for a PDF that cannot be read, 502 for an
            answer that does not fit the record, 503 when the model
            cannot be reached or the budget is spent.
    """
    # log.debug("Runs the extraction")
    try:
        # log.debug("Returns the extraction")
        return extract(svc.model(), charge, notice)
    except UnreadableDocumentError as error:
        # log.debug("Answers 422: the file is the problem")
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except StructuredOutputError as error:
        # log.debug("Answers 502: the model's answer did not fit, even after a repair")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "the model's answer did not fit the record; try again"
        ) from error
    except BudgetExceededError as error:
        # log.debug("Answers 503: this process has spent its budget")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "the spending limit is reached"
        ) from error
    except Exception as error:
        # log.debug("Re-raises anything that is not a provider outage")
        if not is_transient(error):
            # log.debug("Lets the edge answer a plain 500")
            raise
        # log.debug("Answers 503: the provider failed after every retry")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "the model could not be reached; try again later"
        ) from error


# log.debug("Defines the uploaded file's name as shown, never used as a path")
def _name(upload: UploadFile) -> str:
    """Return the upload's file name, shortened, for display only."""
    # log.debug("Returns the name, cut to a sensible length")
    return (upload.filename or CHARGE_FILE)[:NAME_CHARS]


# log.debug("Defines starting a review")
def _start(svc: Services, ex: Extraction, *, source: str) -> Review:
    """Store a new review of `ex` under this request's id."""
    # log.debug("Adds the review")
    review = svc.reviews.add(ex, source=source, demo=svc.demo, request_id=current_request_id())
    # log.debug("Logs it, with what the extraction cost")
    log_event(log, "review.started", review_id=review.review_id, cost_usd=ex.cost_usd)
    # log.debug("Returns it")
    return review


# log.debug("Defines finding a review or answering 404")
def _review(svc: Services, review_id: str) -> Review:
    """Return the review, or raise 404."""
    # log.debug("Finds it")
    review = svc.reviews.get(review_id)
    # log.debug("Answers 404 when it does not exist")
    if review is None:
        # log.debug("Raises 404")
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_REVIEW)
    # log.debug("Returns it")
    return review


# log.debug("Defines reading a folder's evaluation runs")
def _runs(folder: Path) -> list[dict[str, Any]]:
    """Return the run files in `folder`, skipping other JSON files."""
    # log.debug("Reads every JSON file in the folder")
    found = [json.loads(p.read_text(encoding=ENCODING)) for p in sorted(folder.glob("*.json"))]
    # log.debug("Returns those that are runs, which have results")
    return [run for run in found if isinstance(run, dict) and "results" in run]
