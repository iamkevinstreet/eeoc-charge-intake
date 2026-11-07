########################################################################
#                                                                      #
#                      backend/tests/conftest.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-07

Sets up every test: offline, in an empty folder, with fresh settings,
and the ten generated samples the session shares. Every span is
recorded in memory, never sent.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

# Third-party
import pytest
from kds.logs import get_logger
from kds.logs.spans import Stamp
from kds.logs.steps import KEEPER
from kds.settings import get_settings
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Local
from eeoc_intake.config import AppSettings, get_app_settings
from eeoc_intake.core.generate import generate
from support import make_settings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Holds every span the tests open, in memory")
MEMORY = InMemorySpanExporter()


########################################################################
#                                                                      #
#                            Test fixtures                             #
#                                                                      #
########################################################################
# log.debug("Defines the isolation every test gets")
@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Runs in an empty folder, offline, with no cached settings.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        monkeypatch: pytest's helper for patching the environment and
            objects.

    Yields:
        Control to the test; the cached settings are cleared after.
    """
    # log.debug("Moves into an empty folder, so no .env or settings file leaks in")
    monkeypatch.chdir(tmp_path)
    # log.debug("Selects the offline stand-in")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    # log.debug("Sends log files to the temp folder")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    # log.debug("Forgets settings cached by an earlier test")
    get_settings.cache_clear()
    # log.debug("Forgets this package's cached settings too")
    get_app_settings.cache_clear()
    # log.debug("Runs the test")
    yield
    # log.debug("Leaves no settings cached for the next test")
    get_app_settings.cache_clear()


# log.debug("Defines the ten generated samples, made once per session")
@pytest.fixture(scope="session")
def samples(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Ten documents from seed 7; the fifth and tenth are hard cases.

    Args:
        tmp_path_factory: pytest's maker of temporary folders for the
            session.

    Returns:
        The folder holding the documents and cases.jsonl.
    """
    # log.debug("Makes a folder for the session")
    out = tmp_path_factory.mktemp("samples")
    # log.debug("Generates the documents and cases.jsonl into it")
    generate(AppSettings(samples_count=10, samples_seed=7, data_samples=out))
    # log.debug("Returns the folder")
    return out


# log.debug("Defines settings that read the samples and write to tmp_path")
@pytest.fixture
def settings(tmp_path: Path, samples: Path) -> AppSettings:
    """Returns offline settings over the samples, writing in tmp_path.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        samples: The folder of the session's generated samples.

    Returns:
        The settings.
    """
    # log.debug("Returns them")
    return make_settings(tmp_path, samples)


# log.debug("Defines the span recorder every test in the session shares")
@pytest.fixture(scope="session", autouse=True)
def recorded() -> Iterator[None]:
    """Records every span in memory, stamped and kept as in a service.

    Yields:
        Nothing; the session runs while the fixture waits here.
    """
    # log.debug("Creates the provider every test's spans go to")
    provider = TracerProvider()
    # log.debug("Stamps each span with its request id and session")
    provider.add_span_processor(Stamp())
    # log.debug("Records each span in memory as it ends")
    provider.add_span_processor(SimpleSpanProcessor(MEMORY))
    # log.debug("Lets evaluation runs keep their spans")
    provider.add_span_processor(KEEPER)
    # log.debug("Puts it in use for the session")
    trace.set_tracer_provider(provider)
    # log.debug("Runs the session")
    yield


# log.debug("Defines the spans one test records")
@pytest.fixture
def spans() -> InMemorySpanExporter:
    """Returns the span recorder, cleared of earlier tests' spans.

    Returns:
        The recorder; get_finished_spans() lists this test's spans.
    """
    # log.debug("Forgets the spans earlier tests recorded")
    MEMORY.clear()
    # log.debug("Returns the recorder")
    return MEMORY
