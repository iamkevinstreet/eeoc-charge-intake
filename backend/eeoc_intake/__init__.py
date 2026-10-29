########################################################################
#                   backend/eeoc_intake/__init__.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The charge intake package: its version, reported #
#                     by the health check.                             #
########################################################################
"""EEOC charge intake: extraction with evidence and human review."""

from __future__ import annotations

from kds.logs import get_logger

# Module constants
log = get_logger(__name__)
# log.debug("Sets the release, reported by the health check")
__version__ = "0.4.0"
