########################################################################
#                      backend/tests/conftest.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Sets up every test: offline, in an empty folder, with fresh settings,
and the ten generated samples the session shares.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

# Third-party
import pytest
from kds.logs import get_logger
from kds.settings import get_settings

# Local
from eeoc_intake.config import AppSettings, get_app_settings
from eeoc_intake.core.generate import generate
from support import make_settings

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                            Test fixtures                             #
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
