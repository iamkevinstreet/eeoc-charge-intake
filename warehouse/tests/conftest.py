########################################################################
#                                                                      #
#                     warehouse/tests/conftest.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Runs every test from the repository's root, where config/config.toml
and the dbt project are found, with dlt's telemetry off and the
warehouse set to DuckDB, so a test never reaches Databricks whatever
config/.env or the shell says.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
import pytest
from kds.logs import get_logger

# Local
from support import REPO

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                             Test set-up                              #
#                                                                      #
########################################################################
# log.debug("Defines the set-up every test runs in")
@pytest.fixture(autouse=True)
def _at_the_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Moves to the repository's root and keeps the warehouse local.

    Args:
        monkeypatch: pytest's way to change the process for one test.
    """
    # log.debug("Moves to the root")
    monkeypatch.chdir(REPO)
    # log.debug("Turns dlt's usage telemetry off")
    monkeypatch.setenv("RUNTIME__DLTHUB_TELEMETRY", "false")
    # log.debug("Loads into DuckDB, whatever config/.env says")
    monkeypatch.setenv("WAREHOUSE_DESTINATION", "duckdb")
    # log.debug("Builds with dbt's DuckDB target, whatever config/.env says")
    monkeypatch.setenv("DBT_TARGET", "dev")
