########################################################################
#                backend/src/eeoc_intake/api/routes.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Serves the review routes, all under the API's prefix (/api/v1):

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

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Final

# Third-party
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi import Path as PathParam
from kds.args import required
from kds.evals.case import EvalCase
from kds.logs import current_request_id, get_logger, log_event

# Local
from eeoc_intake import __version__
from eeoc_intake.api.extraction import (
    check_limit,
    extract_uploads,
    run_extraction,
    upload_name,
)
from eeoc_intake.api.reviews import Review, exported, payload, undecided
from eeoc_intake.api.state import Services, services
from eeoc_intake.config import SETTINGS
from eeoc_intake.core.extract import Extraction
from eeoc_intake.core.schema import FIELDS, Decision

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the prefix of every route, from the config")
PREFIX: Final = SETTINGS.api_prefix
# log.debug("Takes the encoding of the results files, from the config")
ENCODING: Final = SETTINGS.files_encoding
# log.debug("Takes the input that holds a case's charge PDF, from the config")
CHARGE_PDF: Final = SETTINGS.samples_charge_input
# log.debug("Takes the input that holds a case's notice PDF, from the config")
NOTICE_PDF: Final = SETTINGS.samples_notice_input
# log.debug("Takes the key only a run's results file has, from the config")
RESULTS: Final = SETTINGS.eval_results_key

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the pattern of a sample id")
SAMPLE_ID: Final = r"^charge-\d{3,6}$"
# log.debug("Sets the pattern of a review id")
REVIEW_ID: Final = r"^[0-9a-f]{10}$"
# log.debug("Sets the reply when a review does not exist")
NO_REVIEW: Final = "no such review"


########################################################################
#                            Review routes                             #
########################################################################
# log.debug("Builds the router every route hangs from")
router = APIRouter(prefix=PREFIX)


# log.debug("Types the services every route depends on")
Svc = Annotated[Services, Depends(services)]


# log.debug("Types a review id in a path")
ReviewId = Annotated[str, PathParam(pattern=REVIEW_ID)]


# log.debug("Defines the health check")
@router.get("/health")
def health(svc: Svc) -> dict[str, Any]:
    """Reports the version, provider, model, and whether it is a demo.

    Args:
        svc: The shared services.

    Returns:
        Whether the service is up, its version, the provider and the
        model, and whether this is demo mode.
    """
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
    """Returns the generated documents, by id, kind and file name.

    Args:
        svc: The shared services.

    Returns:
        Each sample's id, its kinds and the names of its two files.
    """
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
    """Extracts an uploaded charge and notice and starts their review.

    Args:
        charge: The uploaded charge form, a PDF.
        notice: The uploaded notice letter, a PDF.
        request: The request, whose client the limit counts.
        svc: The shared services.

    Returns:
        The new review, as the review screen reads it.

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
    check_limit(svc, request)
    # log.debug("Reads, saves and extracts both files")
    ex = extract_uploads(svc, charge, notice)
    # log.debug("Starts the review and returns it")
    return payload(_start(svc, ex, source=f"upload:{upload_name(charge)}"))


# log.debug("Defines extraction from a generated sample")
@router.post("/extract/sample/{sample_id}")
def extract_sample(
    sample_id: Annotated[str, PathParam(pattern=SAMPLE_ID)], request: Request, svc: Svc
) -> dict[str, Any]:
    """Extracts one generated sample and starts its review.

    Args:
        sample_id: The sample's id, such as charge-000.
        request: The request, whose client the limit counts.
        svc: The shared services.

    Returns:
        The new review, as the review screen reads it.

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
        check_limit(svc, request)
    # log.debug("Extracts the sample's two documents")
    ex = run_extraction(svc, case.input[CHARGE_PDF], case.input[NOTICE_PDF])
    # log.debug("Starts the review and returns it")
    return payload(_start(svc, ex, source=f"sample:{sample_id}"))


# log.debug("Defines reading a review")
@router.get("/reviews/{review_id}")
def get_review(review_id: ReviewId, svc: Svc) -> dict[str, Any]:
    """Returns the review with its decisions so far.

    Args:
        review_id: The review's id.
        svc: The shared services.

    Returns:
        The review, as the review screen reads it.
    """
    # log.debug("Returns the review")
    return payload(_review(svc, review_id))


# log.debug("Defines recording a decision")
@router.post("/reviews/{review_id}/decisions")
def decide(review_id: ReviewId, decision: Decision, svc: Svc) -> dict[str, int]:
    """Records a decision on one field and reports the progress.

    Args:
        review_id: The review's id.
        decision: The reviewer's decision on one field.
        svc: The shared services.

    Returns:
        How many fields are decided, out of how many.

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
    """Returns the decided record, once every field is decided.

    Args:
        review_id: The review's id.
        svc: The shared services.

    Returns:
        The record after the decisions, its response deadline and each
        field's decision.

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
    """Returns the newest live run, or the newest smoke run without one.

    Args:
        svc: The shared services.

    Returns:
        The newest run's results file, as it is saved.

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


# log.debug("Defines starting a review")
def _start(
    svc: Services | None = None, ex: Extraction | None = None, *, source: str | None = None
) -> Review:
    """Stores a new review of `ex` under this request's id.

    Args:
        svc: The shared services, which hold the reviews. Required.
        ex: The extraction to review. Required.
        source: Where the documents came from: sample:<id> or
            upload:<name>. Required.

    Returns:
        The new review.
    """
    # log.debug("Takes the services, which the caller must give")
    svc = required(svc=svc)
    # log.debug("Takes the extraction, which the caller must give")
    ex = required(ex=ex)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Adds the review")
    review = svc.reviews.add(ex, source=source, demo=svc.demo, request_id=current_request_id())
    # log.debug("Logs it, with what the extraction cost")
    log_event(log, "review.started", review_id=review.review_id, cost_usd=ex.cost_usd)
    # log.debug("Returns it")
    return review


# log.debug("Defines finding a review or answering 404")
def _review(svc: Services | None = None, review_id: str | None = None) -> Review:
    """Returns the review, or answers 404 when there is none.

    Args:
        svc: The shared services, which hold the reviews. Required.
        review_id: The review's id. Required.

    Returns:
        The review.

    Raises:
        HTTPException: 404 when no review has the id.
    """
    # log.debug("Takes the services, which the caller must give")
    svc = required(svc=svc)
    # log.debug("Takes the review id, which the caller must give")
    review_id = required(review_id=review_id)
    # log.debug("Finds it")
    review = svc.reviews.get(review_id)
    # log.debug("Answers 404 when it does not exist")
    if review is None:
        # log.debug("Raises 404")
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_REVIEW)
    # log.debug("Returns it")
    return review


# log.debug("Defines reading a folder's evaluation runs")
def _runs(folder: Path | None = None) -> list[dict[str, Any]]:
    """Returns the run files in `folder`, skipping other JSON files.

    Args:
        folder: The folder of results files. Required.

    Returns:
        Each run in the folder, in file-name order.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Reads every JSON file in the folder")
    found = [json.loads(p.read_text(encoding=ENCODING)) for p in sorted(folder.glob("*.json"))]
    # log.debug("Returns those that are runs, which have results")
    return [run for run in found if isinstance(run, dict) and RESULTS in run]
