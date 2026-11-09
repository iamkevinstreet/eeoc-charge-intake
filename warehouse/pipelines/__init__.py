########################################################################
#                                                                      #
#                   warehouse/pipelines/__init__.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

EEOC charge warehouse's loaders and the one command the schedules run.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
from kds.logs import get_logger

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)
