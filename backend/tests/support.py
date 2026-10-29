########################################################################
#                       backend/tests/support.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Shared test helpers: the repository root, test   #
#                     settings, a started client, scripted models.     #
########################################################################
"""Shared test helpers: the repository root, settings and clients."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from kds.llm import ModelAdapter
from kds.llm.fake import FakeProvider
from kds.logs import get_logger

from eeoc_intake.api.app import create_app
from eeoc_intake.config import AppSettings

# Module constants
log = get_logger(__name__)
# log.debug("Finds the repository root, two folders above this file")
REPO = Path(__file__).resolve().parents[2]
# log.debug("Sets the address the test client calls, which the host check allows")
LOCAL = "http://127.0.0.1"


# log.debug("Defines settings that read the samples and write to a temp folder")
def make_settings(tmp: Path, samples: Path, **overrides: Any) -> AppSettings:
    """Return settings that write only under `tmp`."""
    # log.debug("Returns the settings, offline unless overridden")
    return AppSettings(
        **{
            "llm_provider": "fake",
            "data_samples": samples,
            "data_results": tmp / "results",
            "data_smoke": tmp / "smoke",
            "data_extractions": tmp / "extractions",
            "data_export": tmp / "export",
            "log_dir": tmp / "logs",
            "ui_dist": tmp / "no-ui",
            **overrides,
        }
    )


# log.debug("Defines a started test client")
@contextmanager
def started(settings: AppSettings, adapter: ModelAdapter | None = None) -> Iterator[TestClient]:
    """Yield a started client addressed to this machine."""
    # log.debug("Starts the app and yields the client")
    with TestClient(create_app(settings, adapter=adapter), base_url=LOCAL) as client:
        # log.debug("Yields it")
        yield client


# log.debug("Defines a model that always gives the same answer")
def scripted(settings: AppSettings, answer: str) -> ModelAdapter:
    """Return an adapter whose model answers `answer` every time."""
    # log.debug("Returns the adapter, with no waits between retries")
    return ModelAdapter(
        FakeProvider(responder=lambda _: answer),
        model="scripted",
        settings=settings,
        sleep=lambda _: None,
    )
