########################################################################
#                    backend/eeoc_intake/api/app.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Builds the HTTP app: startup, request ids,       #
#                     security headers, hosts, size limits, the UI.    #
########################################################################
"""The FastAPI app factory.

Every response carries the request id and security headers; requests
to a host name not in settings are refused (which stops DNS-rebinding
pages reaching a local server); bodies over the size limit are refused
before they are read; every request is logged as one JSON line; and an
unplanned error comes back as a plain 500 with nothing internal. When
the review screen has been built, the service serves it at /.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from kds.llm import ModelAdapter
from kds.logs import get_logger, log_event, new_request_id, setup_logging
from kds.settings import describe

from eeoc_intake import __version__
from eeoc_intake.api import routes
from eeoc_intake.api.state import PREFIX, build_services
from eeoc_intake.config import AppSettings, get_app_settings

# Module constants
log = get_logger(__name__)
# log.debug("Names the service")
SERVICE: Final = "EEOC charge intake"
# log.debug("Names the request id header")
REQUEST_ID: Final = "X-Request-ID"
# log.debug("Sets the shape of a request id a client may send")
REQUEST_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# log.debug("Sets the headers every response carries; the UI has its own")
SECURITY_HEADERS: Final = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
}
# log.debug("Sets the extra headers of API responses, which no browser renders")
API_HEADERS: Final = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}
# log.debug("Sets the policy for the built review screen")
UI_POLICY: Final = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; font-src 'self'; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)
# log.debug("Sets the room multipart framing needs around two uploads")
UPLOAD_SLACK_BYTES: Final = 64_000
# log.debug("Sets the largest body any other request may send")
JSON_MAX_BYTES: Final = 64_000
# log.debug("Sets the path of the one route that takes uploads")
UPLOAD_PATH: Final = f"{PREFIX}/extract"
# log.debug("Sets the milliseconds in a second")
MS: Final = 1000
# log.debug("Lists the methods that carry a body")
BODY_METHODS: Final = frozenset({"POST", "PUT", "PATCH"})
# log.debug("Names the length header")
CONTENT_LENGTH: Final = "content-length"
# log.debug("Names the error message key")
DETAIL: Final = "detail"
# log.debug("Types the next handler in the chain")
Next = Callable[[Request], Awaitable[Response]]


# log.debug("Defines the app factory")
def create_app(
    settings: AppSettings | None = None, *, adapter: ModelAdapter | None = None
) -> FastAPI:
    """Build the app; tests pass settings and an adapter."""
    # log.debug("Uses the shared settings unless given")
    config = settings or get_app_settings()

    # log.debug("Defines startup: logging, the settings in the log, the services")
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Set up logging, log every setting (secrets masked), build."""
        # log.debug("Starts logging to the configured folder")
        setup_logging(config)
        # log.debug("Logs the version and every setting, secrets masked")
        log_event(log, "service.start", version=__version__, settings=describe(config))
        # log.debug("Builds the services the routes share")
        app.state.services = build_services(config, adapter)
        # log.debug("Serves until shutdown")
        yield

    # log.debug("Builds the app, with the API's schema under its prefix")
    app = FastAPI(
        title=SERVICE,
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=f"{PREFIX}/openapi.json",
    )
    # log.debug("Refuses requests for any host name not in settings")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.api_allowed_hosts))
    # log.debug("Lets the dev server's origin call the API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.api_allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", REQUEST_ID],
        expose_headers=[REQUEST_ID],
    )
    # log.debug("Adds the edge last, so it wraps everything, refusals included")
    app.middleware("http")(_edge(2 * config.api_max_upload_bytes + UPLOAD_SLACK_BYTES))
    # log.debug("Mounts the routes")
    app.include_router(routes.router)
    # log.debug("Serves the built review screen at /, or says how to build it")
    if config.ui_dist.is_dir():
        # log.debug("Mounts the built files, with index.html for /")
        app.mount("/", StaticFiles(directory=config.ui_dist, html=True), name="screen")
    else:
        # log.debug("Answers / with where the API is and how to build the screen")
        app.get("/")(_unbuilt)
    # log.debug("Returns the app")
    return app


# log.debug("Defines the answer at / before the review screen is built")
def _unbuilt() -> dict[str, str]:
    """Say where the API is and how to build the review screen."""
    # log.debug("Returns the pointers")
    return {
        "service": SERVICE,
        "api": PREFIX,
        "ui": "run make build to serve the review screen here, or make web for the dev server",
    }


# log.debug("Defines the edge middleware")
def _edge(max_upload: int) -> Callable[[Request, Next], Awaitable[Response]]:
    """Return middleware that ids, limits, logs and secures."""

    # log.debug("Defines the middleware itself")
    async def edge(request: Request, call_next: Next) -> Response:
        """Run the request under its id; refuse oversized bodies."""
        # log.debug("Reads the client's request id, if it sent a valid one")
        given = request.headers.get(REQUEST_ID, "")
        # log.debug("Starts the clock")
        started = time.perf_counter()
        # log.debug("Runs the request under that id or a new one")
        with new_request_id(given if REQUEST_ID_RE.fullmatch(given) else None) as request_id:
            # log.debug("Allows uploads their limit and every other body a small one")
            limit = max_upload if request.url.path == UPLOAD_PATH else JSON_MAX_BYTES
            # log.debug("Answers the request, or refuses its body")
            response = await _answer(request, call_next, limit)
            # log.debug("Adds the security headers and the request id")
            response.headers.update({**SECURITY_HEADERS, REQUEST_ID: request_id})
            # log.debug("Adds the headers for an API answer or for the review screen")
            response.headers.update(
                API_HEADERS
                if request.url.path.startswith(PREFIX)
                else {"Content-Security-Policy": UI_POLICY}
            )
            # log.debug("Logs the request as one line")
            log_event(
                log,
                "http.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=int((time.perf_counter() - started) * MS),
            )
        # log.debug("Returns the response")
        return response

    # log.debug("Returns the middleware")
    return edge


# log.debug("Defines the body checks and the last line of error handling")
async def _answer(request: Request, call_next: Next, max_body: int) -> Response:
    """Refuse a body with no declared length or one over the limit.

    A chunked body declares no length, so it could only be measured by
    reading it; it is refused instead. An error nobody planned for
    becomes a plain 500 here, so it still carries the headers.
    """
    # log.debug("Reads the declared length")
    length = request.headers.get(CONTENT_LENGTH)
    # log.debug("Refuses a body that does not declare its length")
    if length is None and request.method in BODY_METHODS:
        # log.debug("Answers 411")
        return JSONResponse(
            {DETAIL: "send the body with a Content-Length"}, status.HTTP_411_LENGTH_REQUIRED
        )
    # log.debug("Refuses a length that is not a number or is over the limit")
    if length is not None and (not length.isdigit() or int(length) > max_body):
        # log.debug("Answers 413")
        return JSONResponse({DETAIL: "request body too large"}, status.HTTP_413_CONTENT_TOO_LARGE)
    # log.debug("Passes the request on")
    try:
        # log.debug("Returns the app's response")
        return await call_next(request)
    except Exception as error:  # noqa: BLE001 - an unplanned error still gets a reply with headers
        # log.debug("Logs the error's kind, never its message, which may hold data")
        log_event(log, "http.error", logging.ERROR, error=type(error).__name__)
        # log.debug("Answers a plain 500")
        return JSONResponse({DETAIL: "internal error"}, status.HTTP_500_INTERNAL_SERVER_ERROR)
