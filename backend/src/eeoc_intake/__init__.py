########################################################################
#                 backend/src/eeoc_intake/__init__.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The charge intake package: its version, reported by the health check.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
from kds.logs import get_logger

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the release, reported by the health check")
__version__ = "0.5.0"
