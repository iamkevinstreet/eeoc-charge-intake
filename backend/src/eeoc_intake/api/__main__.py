########################################################################
#               backend/src/eeoc_intake/api/__main__.py                #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Runs the review service with uvicorn on the configured host and port.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
import uvicorn
from kds.logs import get_logger

# Local
from eeoc_intake.api.app import create_app
from eeoc_intake.config import get_app_settings

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)


########################################################################
#                             Command line                             #
########################################################################
# log.debug("Defines the command")
def main() -> None:
    """Serves the app; the service logs each request itself."""
    # log.debug("Reads the settings")
    settings = get_app_settings()
    # log.debug("Serves on this machine only, as the settings insist")
    uvicorn.run(
        create_app(settings), host=settings.api_host, port=settings.api_port, access_log=False
    )


# log.debug("Runs the command when the module is run as a script")
if __name__ == "__main__":
    # log.debug("Calls main")
    main()
