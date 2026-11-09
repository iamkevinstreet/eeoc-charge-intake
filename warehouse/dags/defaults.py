########################################################################
#                                                                      #
#                      warehouse/dags/defaults.py                      #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

What every DAG shares: retries, a timeout, one run at a time, and the
one command every task runs, `python -m pipelines`, in the project's
own environment. Airflow only schedules and retries: the loaders and
dbt never run inside the scheduler, so the two never share packages,
and the same command runs from a laptop, CI or a hosted Airflow.

Each load's DAG names the raw schema it writes as an asset, listed in
RAW_SCHEMAS, and BUILD_SCHEDULE runs the warehouse build when any of
them changes, not on a clock of its own.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

# Third-party
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Asset, AssetAny
from kds.args import required
from kds.logs import get_logger

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
# log.debug("Names the variable that can say where the project is, as a container sets it")
HOME: Final = "EEOC_CHARGE_INTAKE_WAREHOUSE_HOME"
# log.debug("Sets where the project is: the variable's say, else this folder's parent")
REPO: Final = os.environ.get(HOME, str(Path(__file__).resolve().parents[1]))
# log.debug("Sets the command every task runs, in the project's locked environment")
PIPELINES: Final = "uv run --no-sync python -m pipelines"
# log.debug("Sets the day the schedules start counting from")
START: Final = datetime(2026, 11, 1, tzinfo=UTC)
# log.debug("Sets what every task inherits: retries with backoff and a time limit")
TASK_DEFAULTS: Final[dict[str, Any]] = {
    "owner": "eeoc-charge-intake",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=30),
}
# log.debug("Sets what every DAG shares: no backfill and one run at a time")
DAG_DEFAULTS: Final[dict[str, Any]] = {
    "start_date": START,
    "catchup": False,
    "max_active_runs": 1,
    "default_args": TASK_DEFAULTS,
}
# log.debug("Names the raw schema the review exports load into")
RAW_REVIEWS: Final = Asset(name="raw_reviews", group="warehouse")
# log.debug("Names the raw schema the EEOC's statistics load into")
RAW_EEOC_STATS: Final = Asset(name="raw_eeoc_stats", group="warehouse")
# log.debug("Lists the raw schema each load writes, as an asset")
RAW_SCHEMAS: Final[tuple[Asset, ...]] = (RAW_REVIEWS, RAW_EEOC_STATS)
# log.debug("Sets what starts the build: a change to any raw schema; until one exists, a person")
BUILD_SCHEDULE: Final = AssetAny(*RAW_SCHEMAS) if RAW_SCHEMAS else None


########################################################################
#                                                                      #
#                              DAG parts                               #
#                                                                      #
########################################################################
# log.debug("Defines a task that runs the project's command")
def pipelines_task(
    task_id: str | None = None, args: str | None = None, outlets: list[Asset] | None = None
) -> BashOperator:
    """Returns a task running `python -m pipelines <args>` at the repo.

    Args:
        task_id: The task's name in the DAG. Required.
        args: What follows the command, such as "load charges".
            Required.
        outlets: The assets the task updates, if any.

    Returns:
        The task.
    """
    # log.debug("Takes the task's name, which the caller must give")
    task_id = required(task_id=task_id)
    # log.debug("Takes the command's arguments, which the caller must give")
    args = required(args=args)
    # log.debug("Returns the task, run at the repository with the environment kept")
    return BashOperator(
        task_id=task_id,
        bash_command=f"{PIPELINES} {args}",
        cwd=REPO,
        append_env=True,
        outlets=outlets or [],
    )
