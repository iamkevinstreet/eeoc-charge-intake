########################################################################
#                                                                      #
#                   warehouse/pipelines/__main__.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

The one command the Makefile, CI and the Airflow DAGs run:

    python -m pipelines load reviews      the review exports
    python -m pipelines load receipts     the EEOC's receipts table
    python -m pipelines dbt build         any dbt command, such as build

Each source's module defines its load, which LOADS names. Every load
reads its destination from config/config.toml, and dbt gets the same
warehouse through profiles.yml's variables.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final

# Third-party
from kds.logs import get_logger
from kds.pipelines import run_command

# Local
from pipelines.config import AppSettings, get_app_settings
from pipelines.receipts import load_receipts
from pipelines.reviews import load_reviews

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)
# log.debug("Lists every load by its name on the command line")
LOADS: Final[dict[str, Callable[[AppSettings], None]]] = {
    "reviews": load_reviews,
    "receipts": load_receipts,
}


########################################################################
#                                                                      #
#                             The command                              #
#                                                                      #
########################################################################
# log.debug("Defines the command line")
def main(argv: Sequence[str] | None = None) -> int:
    """Runs one load or one dbt command.

    Args:
        argv: The command's arguments; the process's own when None.

    Returns:
        0 on success; 1 when dbt failed. A failed load raises.
    """
    # log.debug("Runs the shared command with this project's loads")
    return run_command(LOADS, get_app_settings, argv)


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Exits with main's status")
    raise SystemExit(main())
