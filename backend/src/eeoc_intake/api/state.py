########################################################################
#                 backend/src/eeoc_intake/api/state.py                 #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The services every route shares, built once when #
#                     the app starts: samples, model, reviews, limits. #
########################################################################
"""The services the routes share, built once when the app starts."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from fastapi import Request
from kds.evals.case import EvalCase, load_cases
from kds.llm import ModelAdapter
from kds.logs import get_logger

from eeoc_intake.api.limits import RateLimiter
from eeoc_intake.api.reviews import ReviewStore
from eeoc_intake.config import AppSettings
from eeoc_intake.core.generate import CASES_FILE
from eeoc_intake.core.offline import FAKE, adapter_for

# Module constants
log = get_logger(__name__)
# log.debug("Sets the prefix of every route, which carries the API's version")
PREFIX: Final = "/api/v1"


# log.debug("Defines the generated samples, read again when the file changes")
class Samples:
    """The generated samples; `make samples` needs no restart."""

    # log.debug("Defines the constructor")
    def __init__(self, path: Path) -> None:
        """Read the cases when first used and whenever they change."""
        # log.debug("Keeps the cases file")
        self.path = path
        # log.debug("Starts with no file seen")
        self._stamp: float | None = None
        # log.debug("Starts with no cases")
        self._cases: tuple[EvalCase, ...] = ()
        # log.debug("Guards the cache across request threads")
        self._lock = threading.Lock()

    # log.debug("Defines the current samples")
    def all(self) -> tuple[EvalCase, ...]:
        """Return the cases, re-read if the file changed or appeared."""
        # log.debug("Reads the file's change time, or None before it exists")
        stamp = self.path.stat().st_mtime if self.path.exists() else None
        # log.debug("Re-reads under the lock when the file changed")
        with self._lock:
            # log.debug("Re-reads only when the time differs from the last read")
            if stamp != self._stamp:
                # log.debug("Loads the cases, or none when the file is gone")
                self._cases = tuple(load_cases(self.path)) if stamp is not None else ()
                # log.debug("Remembers the time read")
                self._stamp = stamp
            # log.debug("Returns the cases")
            return self._cases

    # log.debug("Defines finding a sample by id")
    def get(self, sample_id: str) -> EvalCase | None:
        """Return the sample with this id, or None."""
        # log.debug("Returns the first sample with the id, or None")
        return next((s for s in self.all() if s.id == sample_id), None)


# log.debug("Defines the shared services")
@dataclass(frozen=True)
class Services:
    """Everything a route needs, built once per app.

    Attributes:
        settings: The settings the app started with.
        adapter: The model; None in demo mode, where the stand-in is
            built per extraction over the current samples.
        samples: The generated documents a reviewer may open.
        reviews: The reviews in progress.
        limiter: The per-client limit on extractions.
    """

    # log.debug("Holds the settings")
    settings: AppSettings
    # log.debug("Holds the adapter, or None in demo mode")
    adapter: ModelAdapter | None
    # log.debug("Holds the generated samples")
    samples: Samples
    # log.debug("Holds the reviews")
    reviews: ReviewStore
    # log.debug("Holds the limiter")
    limiter: RateLimiter

    # log.debug("Defines demo mode")
    @property
    def demo(self) -> bool:
        """True when the offline stand-in answers, not a model."""
        # log.debug("Returns whether the provider is the stand-in")
        return self.settings.llm_provider == FAKE

    # log.debug("Defines the model an extraction uses")
    def model(self) -> ModelAdapter:
        """Return the adapter, or a stand-in that knows every sample."""
        # log.debug("Returns the shared adapter when there is one")
        if self.adapter is not None:
            # log.debug("Returns it")
            return self.adapter
        # log.debug("Returns the stand-in over the samples as they are now")
        return adapter_for(self.settings, list(self.samples.all()))


# log.debug("Defines building the services")
def build_services(settings: AppSettings, adapter: ModelAdapter | None = None) -> Services:
    """Build the adapter, the samples, the store and the limiter.

    Tests pass an adapter; the service builds one from settings, except
    in demo mode, where each extraction gets a stand-in.
    """
    # log.debug("Builds the shared adapter for a real provider")
    if adapter is None and settings.llm_provider != FAKE:
        # log.debug("Builds it from settings")
        adapter = adapter_for(settings, [])
    # log.debug("Returns the services")
    return Services(
        settings=settings,
        adapter=adapter,
        samples=Samples(settings.data_samples / CASES_FILE),
        reviews=ReviewStore(settings.api_max_reviews),
        limiter=RateLimiter(settings.api_extracts_per_minute),
    )


# log.debug("Defines how a route reaches the services")
def services(request: Request) -> Services:
    """Return the services the app built at startup."""
    # log.debug("Returns them from the app's state")
    return cast(Services, request.app.state.services)
