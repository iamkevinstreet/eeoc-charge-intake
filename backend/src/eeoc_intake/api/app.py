########################################################################
#                  backend/src/eeoc_intake/api/app.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Builds the HTTP app: its startup, request ids, security headers,
allowed hosts, body limits and the review screen. Every response
carries the request id and the security headers; a request addressed to
a host name not in the settings is refused, which stops DNS-rebinding
pages reaching a local server; a body over its limit is refused before
it is read; every request is logged as one JSON line; and an unplanned
error comes back as a plain 500 with nothing internal. When the review
screen has been built, the service serves it at /.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Final

# Third-party
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from kds.args import required
from kds.llm import ModelAdapter
from kds.logs import get_logger, log_event, new_request_id, setup_logging
from kds.settings import describe

# Local
from eeoc_intake import __version__
from eeoc_intake.api import routes
from eeoc_intake.api.state import build_services
from eeoc_intake.config import SETTINGS, AppSettings, get_app_settings

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)
# log.debug("Takes the prefix of every route, from the config")
PREFIX: Final = SETTINGS.api_prefix
# log.debug("Takes the request id header's name, from the config")
REQUEST_ID: Final = SETTINGS.api_request_id_header
# log.debug("Takes the milliseconds in a second, from the config")
MS: Final = SETTINGS.units_ms_per_second

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the service")
SERVICE: Final = "EEOC charge intake"
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
# log.debug("Lists the methods that carry a body")
BODY_METHODS: Final = frozenset({"POST", "PUT", "PATCH"})
# log.debug("Names the length header")
CONTENT_LENGTH: Final = "content-length"
# log.debug("Names the error message key")
DETAIL: Final = "detail"
# log.debug("Types the next handler in the chain")
Next = Callable[[Request], Awaitable[Response]]


########################################################################
#                               HTTP app                               #
########################################################################
# log.debug("Defines the app factory")
def create_app(
    settings: AppSettings | None = None, *, adapter: ModelAdapter | None = None
) -> FastAPI:
    """Builds the app; tests pass settings and an adapter.

    Args:
        settings: The settings to run with; None reads the shared ones.
        adapter: The model to call; None builds one from the settings.

    Returns:
        The app, ready to serve.
    """
    # log.debug("Uses the shared settings unless given")
    config = settings or get_app_settings()

    # log.debug("Defines startup: logging, the settings in the log, the services")
    @asynccontextmanager
    async def lifespan(app: FastAPI | None = None) -> AsyncIterator[None]:
        """Sets up logging, logs every setting and builds the services.

        Secrets are masked in the logged settings.

        Args:
            app: The app that is starting. Required.

        Yields:
            Control to the app, which serves until it shuts down.
        """
        # log.debug("Takes the app, which the caller must give")
        app = required(app=app)
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
    """Says where the API is and how to build the review screen.

    Returns:
        The service's name, the API's prefix and how to build the
        screen.
    """
    # log.debug("Returns the pointers")
    return {
        "service": SERVICE,
        "api": PREFIX,
        "ui": "run make build to serve the review screen here, or make web for the dev server",
    }


# log.debug("Defines the edge middleware")
def _edge(max_upload: int | None = None) -> Callable[[Request, Next], Awaitable[Response]]:
    """Returns middleware that ids, limits, logs and secures.

    Args:
        max_upload: The largest body the upload route may send, in
            bytes. Required.

    Returns:
        The middleware, for app.middleware("http").
    """
    # log.debug("Takes the upload limit, which the caller must give")
    max_upload = required(max_upload=max_upload)

    # log.debug("Defines the middleware itself")
    async def edge(  # fixed: Starlette's middleware signature
        request: Request, call_next: Next
    ) -> Response:
        """Runs a request under its id, refusing a body over its limit.

        Args:
            request: The request.
            call_next: The rest of the app, which answers the request.

        Returns:
            The response, with the request id, the security headers
            and the policy for an API answer or the review screen.
        """
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
async def _answer(
    request: Request | None = None, call_next: Next | None = None, max_body: int | None = None
) -> Response:
    """Refuses a body with no declared length or one over the limit.

    A chunked body declares no length, so it could only be measured by
    reading it; it is refused instead. An error nobody planned for
    becomes a plain 500 here, so it still carries the headers.

    Args:
        request: The request. Required.
        call_next: The rest of the app, which answers the request.
            Required.
        max_body: The largest body this request may send, in bytes.
            Required.

    Returns:
        The app's response, or a 411, 413 or 500 with a plain message.
    """
    # log.debug("Takes the request, which the caller must give")
    request = required(request=request)
    # log.debug("Takes the rest of the app, which the caller must give")
    call_next = required(call_next=call_next)
    # log.debug("Takes the body limit, which the caller must give")
    max_body = required(max_body=max_body)
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
