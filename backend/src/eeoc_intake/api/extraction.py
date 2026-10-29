########################################################################
#              backend/src/eeoc_intake/api/extraction.py               #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Runs the extraction behind the two extraction routes: the per-client
limit, reading two uploads into a folder that is deleted afterwards,
and the extraction itself, with each failure it can meet turned into an
HTTP error that says what went wrong. An uploaded file's name is only
ever shown, never used as a path.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Final

# Third-party
from fastapi import HTTPException, Request, UploadFile, status
from kds.args import missing, required
from kds.llm.errors import BudgetExceededError, StructuredOutputError, is_transient
from kds.logs import get_logger

# Local
from eeoc_intake.api.state import Services
from eeoc_intake.core.extract import Extraction, UnreadableDocumentError, extract

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the first bytes of every PDF")
PDF_MAGIC: Final = b"%PDF-"
# log.debug("Sets the most characters of an uploaded file's name kept")
NAME_CHARS: Final = 120
# log.debug("Sets the seconds a client should wait after the limit")
RETRY_AFTER: Final = "60"
# log.debug("Names the file an uploaded charge is saved as")
CHARGE_FILE: Final = "charge.pdf"
# log.debug("Names the file an uploaded notice is saved as")
NOTICE_FILE: Final = "notice.pdf"


########################################################################
#                          Running extraction                          #
########################################################################
# log.debug("Defines the per-client limit")
def check_limit(svc: Services | None = None, request: Request | None = None) -> None:
    """Raises 429 once this client has used this minute's extractions.

    Args:
        svc: The shared services, which hold the limiter. Required.
        request: The request, whose client the limit counts. Required.

    Raises:
        HTTPException: 429, with a Retry-After header, past the limit.
    """
    # log.debug("Takes the services, which the caller must give")
    svc = required(svc=svc)
    # log.debug("Takes the request, which the caller must give")
    request = required(request=request)
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


# log.debug("Defines the extraction of two uploaded files")
def extract_uploads(
    svc: Services | None = None,
    charge: UploadFile | None = None,
    notice: UploadFile | None = None,
) -> Extraction:
    """Reads both uploads, saves them under fixed names and extracts.

    The files are written to a folder that is deleted afterwards.

    Args:
        svc: The shared services. Required.
        charge: The uploaded charge form. Required.
        notice: The uploaded notice letter. Required.

    Returns:
        The extraction of the two documents.

    Raises:
        HTTPException: 413 for a file over the limit, 415 for a file
            that is not a PDF, or any error run_extraction raises.
    """
    # log.debug("Takes the services, which the caller must give")
    svc = required(svc=svc)
    # log.debug("Takes the charge, which the caller must give")
    charge = required(charge=charge)
    # log.debug("Takes the notice, which the caller must give")
    notice = required(notice=notice)
    # log.debug("Reads both files within the size limit, checking each is a PDF")
    files = [_pdf(f, svc.settings.api_max_upload_bytes) for f in (charge, notice)]
    # log.debug("Writes them to a folder that is deleted afterwards")
    with tempfile.TemporaryDirectory() as tmp:
        # log.debug("Names the two files; the uploaded names are never used as paths")
        paths = [Path(tmp) / CHARGE_FILE, Path(tmp) / NOTICE_FILE]
        # log.debug("Writes each file")
        for path, data in zip(paths, files, strict=True):
            # log.debug("Writes one")
            path.write_bytes(data)
        # log.debug("Extracts them, and returns the extraction")
        return run_extraction(svc, *paths)


# log.debug("Defines reading one upload")
def _pdf(upload: UploadFile | None = None, limit: int | None = None) -> bytes:
    """Returns the file's bytes, at most `limit`, checked to be a PDF.

    Args:
        upload: The uploaded file. Required.
        limit: The largest file allowed, in bytes. Required.

    Returns:
        The file's bytes.

    Raises:
        HTTPException: 413 over the limit, 415 for a file not a PDF.
    """
    # log.debug("Takes the upload, which the caller must give")
    upload = required(upload=upload)
    # log.debug("Takes the limit, which the caller must give")
    limit = required(limit=limit)
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
def run_extraction(
    svc: Services | None = None, charge: Path | str | None = None, notice: Path | str | None = None
) -> Extraction:
    """Extracts, turning each known failure into an HTTP error.

    Args:
        svc: The shared services, which hold the model. Required.
        charge: The charge form's PDF. Required.
        notice: The notice letter's PDF. Required.

    Returns:
        The extraction of the two documents.

    Raises:
        HTTPException: 422 for a PDF that cannot be read, 502 for an
            answer that does not fit the record, 503 when the model
            cannot be reached or the budget is spent.
    """
    # log.debug("Takes the services, which the caller must give")
    svc = required(svc=svc)
    # log.debug("Stops when the caller left out the charge")
    if charge is None:
        # log.debug("Raises the missing-argument error")
        raise missing(charge=charge)
    # log.debug("Stops when the caller left out the notice")
    if notice is None:
        # log.debug("Raises the missing-argument error")
        raise missing(notice=notice)
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
def upload_name(upload: UploadFile | None = None) -> str:
    """Returns the upload's file name, shortened, for display only.

    Args:
        upload: The uploaded charge form. Required.

    Returns:
        The name the client sent, at most 120 characters, or the name
        the charge is saved under when it sent none.
    """
    # log.debug("Takes the upload, which the caller must give")
    upload = required(upload=upload)
    # log.debug("Returns the name, cut to a sensible length")
    return (upload.filename or CHARGE_FILE)[:NAME_CHARS]
