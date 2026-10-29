########################################################################
#               backend/src/eeoc_intake/api/__main__.py                #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Runs the review service with uvicorn on the      #
#                     configured host and port.                        #
########################################################################
"""Run the service: python -m eeoc_intake.api."""

from __future__ import annotations

import uvicorn
from kds.logs import get_logger

from eeoc_intake.api.app import create_app
from eeoc_intake.config import get_app_settings

# Module constants
log = get_logger(__name__)


# log.debug("Defines the command")
def main() -> None:
    """Serve the app; the service logs each request itself."""
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
