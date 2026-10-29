########################################################################
#                     backend/tests/test_config.py                     #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests that config/settings.toml lists every      #
#                     default and no secret, and the host rule holds.  #
########################################################################
"""Tests of the settings file and the settings' own checks."""

from __future__ import annotations

import tomllib
from typing import Any

import pytest
from kds.logs import get_logger
from kds.settings.toml import flatten, is_secret
from pydantic import ValidationError

from eeoc_intake.config import AppSettings
from support import REPO

# Module constants
log = get_logger(__name__)


# log.debug("Defines the helper: return config/settings.toml as flat field names and values")
def _file_values() -> dict[str, Any]:
    """Return config/settings.toml as flat field names and values."""
    # log.debug("Reads and flattens the file")
    return flatten(tomllib.loads((REPO / "config" / "settings.toml").read_text(encoding="utf-8")))


# log.debug("Defines the test: the settings file lists every default")
def test_the_settings_file_lists_every_default() -> None:
    """Every setting but secrets is in the file, at its default."""
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
    """Secret fields are never set in settings.toml."""
    # log.debug("Checks no secret field is in the file")
    assert not [n for n in _file_values() if is_secret(AppSettings.model_fields[n])]


# log.debug("Defines the test: servers refuse to listen beyond this machine")
@pytest.mark.parametrize("field", ["api_host", "dashboard_host"])
def test_servers_refuse_to_listen_beyond_this_machine(field: str) -> None:
    """Neither server has sign-in, so others must not reach either."""
    # log.debug("Names an address every machine on the network can reach")
    values: dict[str, Any] = {field: "0.0.0.0"}  # noqa: S104 - the address the check must refuse
    # log.debug("Checks the settings refuse it")
    with pytest.raises(ValidationError, match="must stay on this machine"):
        # log.debug("Builds the settings")
        AppSettings(**values)
