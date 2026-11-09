########################################################################
#                                                                      #
#                   warehouse/tests/test_command.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the one command the Makefile, CI and the DAGs run: a load runs
by its name with this project's settings, a load the project does not
have is refused, and dbt's result is the command's.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

# Third-party
import pytest
from kds.args import required
from kds.logs import get_logger
from kds.pipelines import PipelineSettings
from kds.pipelines import command as shared

# Local
from pipelines import __main__ as command
from pipelines.config import AppSettings
from support import settings_in

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                            Command tests                             #
#                                                                      #
########################################################################
# log.debug("Defines the test that a load runs by its name")
def test_a_load_runs_by_its_name_with_the_projects_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command finds the load in LOADS and passes it the settings.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching objects.
    """
    # log.debug("Keeps a record of the settings each load is given")
    given: list[AppSettings] = []
    # log.debug("Reads the settings from the test's folder")
    monkeypatch.setattr(command, "get_app_settings", lambda: settings_in(tmp_path))
    # log.debug("Names one load that records what it was given")
    monkeypatch.setattr(command, "LOADS", {"sample": given.append})
    # log.debug("Checks the load ran once, with this project's settings")
    assert (command.main(["load", "sample"]), [type(s) for s in given]) == (0, [AppSettings])


# log.debug("Defines the test that an unknown load is refused")
def test_a_load_the_project_does_not_have_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name not in LOADS stops the command before anything runs.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching objects.
    """
    # log.debug("Reads the settings from the test's folder")
    monkeypatch.setattr(command, "get_app_settings", lambda: settings_in(tmp_path))
    # log.debug("Checks the command refuses the name")
    with pytest.raises(SystemExit):
        # log.debug("Runs a load by a name no load has")
        command.main(["load", "no-load-by-this-name"])


# log.debug("Defines the test that dbt's result is the command's")
def test_dbt_gets_every_argument_and_its_failure_fails_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command passes dbt what follows `dbt`, and fails as dbt does.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching objects.
    """
    # log.debug("Keeps a record of each dbt run's settings and command, without running dbt")
    runs: list[tuple[type[PipelineSettings], Sequence[str]]] = []

    # log.debug("Defines a dbt that records its run and fails")
    def failing_dbt(
        settings: PipelineSettings | None = None, args: Sequence[str] | None = None
    ) -> bool:
        """Records the settings' type and the command, and fails.

        Args:
            settings: The settings dbt would run with. Required.
            args: The dbt command and its options. Required.

        Returns:
            False, as a failed dbt does.
        """
        # log.debug("Records the run, with the settings and command the caller must give")
        runs.append((type(required(settings=settings)), required(args=args)))
        # log.debug("Reports the failure")
        return False

    # log.debug("Reads the settings from the test's folder")
    monkeypatch.setattr(command, "get_app_settings", lambda: settings_in(tmp_path))
    # log.debug("Puts the failing dbt in dbt's place")
    monkeypatch.setattr(shared, "run_dbt", failing_dbt)
    # log.debug("Checks the command failed and dbt got the settings and every argument")
    assert (command.main(["dbt", "build", "--select", "staging"]), runs) == (
        1,
        [(AppSettings, ["build", "--select", "staging"])],
    )
