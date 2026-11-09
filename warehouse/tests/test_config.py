########################################################################
#                                                                      #
#                    warehouse/tests/test_config.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the settings file: it lists every setting at its default, so
the file is a true account of what the code does, and it holds no
secret, since those live in config/.env and the environment only.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import tomllib
from typing import Any

# Third-party
from kds.logs import get_logger
from kds.settings import Settings
from kds.settings.toml import flatten, is_secret

# Local
from pipelines.config import AppSettings
from support import REPO

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                             Config tests                             #
#                                                                      #
########################################################################
# log.debug("Defines the file's values")
def _file_values() -> dict[str, Any]:
    """Returns config/config.toml as flat field names and values.

    Returns:
        Each setting's field name mapped to its value in the file.
    """
    # log.debug("Reads and flattens the file")
    return flatten(tomllib.loads((REPO / "config" / "config.toml").read_text(encoding="utf-8")))


# log.debug("Defines the test that the file matches the defaults")
def test_the_settings_file_lists_every_default() -> None:
    """Every setting beyond logging's is in the file, as defaulted."""
    # log.debug("Reads the file")
    values = _file_values()
    # log.debug("Lists the settings the data layers add that are not secrets or connections")
    own = {
        name
        for name, field in AppSettings.model_fields.items()
        if name not in Settings.model_fields and not is_secret(field) and field.default is not None
    }
    # log.debug("Checks the file names each of them")
    assert own <= set(values), own - set(values)
    # log.debug("Checks each value in the file equals its field's default")
    for name, value in values.items():
        # log.debug("Validates the value and compares it with the default")
        assert getattr(AppSettings(**{name: value}), name) == (
            AppSettings.model_fields[name].get_default(call_default_factory=True)
        ), name


# log.debug("Defines the test that the file holds no secret")
def test_the_settings_file_holds_no_secret() -> None:
    """Tokens live in config/.env and the environment only."""
    # log.debug("Lists the secret fields")
    secrets = {n for n, f in AppSettings.model_fields.items() if is_secret(f)}
    # log.debug("Checks none is in the file")
    assert secrets.isdisjoint(_file_values())
