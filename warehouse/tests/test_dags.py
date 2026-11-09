########################################################################
#                                                                      #
#                     warehouse/tests/test_dags.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the DAGs as Airflow itself parses them: every file imports,
every DAG retries, runs once at a time and never backfills, every task
runs the project's command at the repository, the build waits on every
raw schema a load updates, and the Makefile's DAGS names every DAG, so
`make dags-test` runs each one. Skipped unless the airflow group is
installed.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from typing import Any, Final

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
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the DAGs folder, which Airflow puts on the path in production")
DAGS: Final = REPO / "dags"
# log.debug("Sets the command every task must run")
COMMAND: Final = "uv run --no-sync python -m pipelines "
# log.debug("Sets how the Makefile's line of DAG ids starts")
MAKE_DAGS: Final = "DAGS :="


########################################################################
#                                                                      #
#                              DAG tests                               #
#                                                                      #
########################################################################
# log.debug("Defines the DAGs as Airflow parses them")
@pytest.fixture(scope="module")
def dags(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Parses the DAGs folder with Airflow's own DagBag.

    Args:
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        Each DAG by its id.
    """
    # log.debug("Skips when the airflow group is not installed")
    pytest.importorskip("airflow")
    # log.debug("Keeps Airflow's home out of the repository and the user's")
    with pytest.MonkeyPatch.context() as patch:
        # log.debug("Points Airflow's home at a temporary folder")
        patch.setenv("AIRFLOW_HOME", str(tmp_path_factory.mktemp("airflow")))
        # log.debug("Puts the DAGs folder on the path, as the DAG processor does")
        patch.syspath_prepend(str(DAGS))
        # log.debug("Imports the DagBag")
        from airflow.dag_processing.dagbag import DagBag  # noqa: PLC0415

        # log.debug("Parses the folder")
        bag = DagBag(dag_folder=str(DAGS))
    # log.debug("Fails on any file that did not import")
    assert bag.import_errors == {}
    # log.debug("Returns the DAGs")
    return dict(bag.dags)


# log.debug("Defines the test that the Makefile names every DAG")
def test_make_dags_test_runs_every_dag(dags: dict[str, Any]) -> None:
    """The Makefile's DAGS lists exactly the DAGs the folder holds.

    Args:
        dags: The parsed DAGs.
    """
    # log.debug("Reads the Makefile's lines")
    lines = (REPO / "Makefile").read_text(encoding="utf-8").splitlines()
    # log.debug("Takes the ids on the DAGS line")
    listed = next(line for line in lines if line.startswith(MAKE_DAGS)).split()[2:]
    # log.debug("Checks they are the folder's DAGs, each once")
    assert sorted(listed) == sorted(dags)


# log.debug("Defines the test of every DAG's safety settings")
def test_every_dag_retries_runs_once_at_a_time_and_never_backfills(dags: dict[str, Any]) -> None:
    """A failed task retries; a slow run never overlaps the next.

    Args:
        dags: The parsed DAGs.
    """
    # log.debug("Checks each DAG's settings and tags")
    for dag in dags.values():
        # log.debug("Checks the DAG")
        assert (dag.catchup, dag.max_active_runs, bool(dag.tags)) == (False, 1, True), dag.dag_id
        # log.debug("Checks every task retries and has a time limit")
        assert all(t.retries >= 1 and t.execution_timeout for t in dag.tasks), dag.dag_id


# log.debug("Defines the test of every task's command")
def test_every_task_runs_the_projects_command_at_the_repository(dags: dict[str, Any]) -> None:
    """No task runs code inside the scheduler's own environment.

    Args:
        dags: The parsed DAGs.
    """
    # log.debug("Lists every task")
    tasks = [t for dag in dags.values() for t in dag.tasks]
    # log.debug("Checks each runs the command, at the repository")
    assert all(t.bash_command.startswith(COMMAND) and t.cwd == str(REPO) for t in tasks)


# log.debug("Defines the test that the build waits on every load")
def test_the_build_runs_when_any_load_changes_its_raw_schema(dags: dict[str, Any]) -> None:
    """Each asset a load updates is one the build is scheduled on.

    Args:
        dags: The parsed DAGs.
    """
    # log.debug("Lists the assets the loads update")
    updated = sorted(o.name for dag in dags.values() for t in dag.tasks for o in t.outlets)
    # log.debug("Reads what the build is scheduled on, nothing when it waits on no asset")
    condition = getattr(dags["build_warehouse"].timetable, "asset_condition", None)
    # log.debug("Checks the build waits on exactly those assets")
    assert sorted(a.name for a in getattr(condition, "objects", ())) == updated
