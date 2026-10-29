########################################################################
#                     backend/tests/test_config.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests that config/config.toml lists every default and no secret, and the
host rule holds.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import tomllib
from typing import Any

# Third-party
import pytest
from kds.logs import get_logger
from kds.settings.toml import flatten, is_secret
from pydantic import ValidationError

# Local
from eeoc_intake.config import AppSettings
from support import REPO

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                            Settings tests                            #
########################################################################
# log.debug("Defines how the config file is read as flat field names and values")
def _file_values() -> dict[str, Any]:
    """Returns config/config.toml as flat field names and values.

    Returns:
        Each setting's field name mapped to its value in the file.
    """
    # log.debug("Reads and flattens the file")
    return flatten(tomllib.loads((REPO / "config" / "config.toml").read_text(encoding="utf-8")))


# log.debug("Defines the test: the settings file lists every default")
def test_the_settings_file_lists_every_default() -> None:
    """Checks every setting but secrets is in the file, as defaulted."""
    # log.debug("Reads the file")
    values = _file_values()
    # log.debug("Lists every field that is not a secret")
    fields = {n for n, f in AppSettings.model_fields.items() if not is_secret(f)}
    # log.debug("Checks the file names each one except the Azure endpoint")
    assert set(values) == fields - {"azure_openai_endpoint"}
    # log.debug("Checks each value, once validated, equals the field's default")
    for name, value in values.items():
        # log.debug("Validates the value through the settings and compares")
        assert getattr(AppSettings(**{name: value}), name) == (
            AppSettings.model_fields[name].default
        ), name


# log.debug("Defines the test: the settings file holds no secret")
def test_the_settings_file_holds_no_secret() -> None:
    """Checks secret fields are never set in config.toml."""
    # log.debug("Checks no secret field is in the file")
    assert not [n for n in _file_values() if is_secret(AppSettings.model_fields[n])]


# log.debug("Defines the test: servers refuse to listen beyond this machine")
@pytest.mark.parametrize("field", ["api_host", "dashboard_host"])
def test_servers_refuse_to_listen_beyond_this_machine(field: str) -> None:
    """Checks neither server listens beyond this machine: no sign-in.

    Args:
        field: The host setting under test.
    """
    # log.debug("Names an address every machine on the network can reach")
    values: dict[str, Any] = {field: "0.0.0.0"}  # noqa: S104 - the address the check must refuse
    # log.debug("Checks the settings refuse it")
    with pytest.raises(ValidationError, match="must stay on this machine"):
        # log.debug("Builds the settings")
        AppSettings(**values)
