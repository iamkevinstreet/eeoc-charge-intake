########################################################################
#                backend/src/eeoc_intake/api/limits.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Limits how many extractions each client may start in a rolling minute.
The recent request times are kept in memory, per client, so the limit
holds for one server process. Behind a proxy or with several workers it
belongs in the proxy or a shared store instead, which the README lists
as unresolved.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

# Third-party
from kds.args import required
from kds.logs import get_logger

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the window the limit counts over, in seconds")
WINDOW_S = 60.0


########################################################################
#                           Per-client limit                           #
########################################################################
# log.debug("Defines the limiter")
class RateLimiter:
    """At most `limit` requests per client in any rolling window."""

    # log.debug("Defines the constructor")
    def __init__(
        self,
        limit: int | None = None,
        window_s: float = WINDOW_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Allows `limit` requests per client per `window_s` seconds.

        Args:
            limit: The most requests one client may make in a window.
                Required.
            window_s: The length of the window, in seconds.
            clock: The clock read at each request; tests pass their own.
        """
        # log.debug("Takes the limit, which the caller must give")
        limit = required(limit=limit)
        # log.debug("Keeps the limit")
        self.limit = limit
        # log.debug("Keeps the window length")
        self.window_s = window_s
        # log.debug("Keeps the clock, which tests replace")
        self.clock = clock
        # log.debug("Starts each client's list of recent request times")
        self._seen: defaultdict[str, deque[float]] = defaultdict(deque)
        # log.debug("Creates the lock that guards those lists")
        self._lock = threading.Lock()

    # log.debug("Defines the check for one request")
    def allow(self, client: str | None = None) -> bool:
        """Records a request, unless the client is over the limit.

        Args:
            client: The client's address. Required.

        Returns:
            True when the request is allowed, False when the client has
            used the window's requests; a refused one is not recorded.
        """
        # log.debug("Takes the client, which the caller must give")
        client = required(client=client)
        # log.debug("Reads the time now")
        now = self.clock()
        # log.debug("Updates the client's list under the lock")
        with self._lock:
            # log.debug("Takes the client's recent request times")
            seen = self._seen[client]
            # log.debug("Forgets requests older than the window")
            while seen and now - seen[0] >= self.window_s:
                # log.debug("Drops the oldest request time")
                seen.popleft()
            # log.debug("Refuses the request when the window is full")
            if len(seen) >= self.limit:
                # log.debug("Returns refused")
                return False
            # log.debug("Records this request")
            seen.append(now)
        # log.debug("Returns allowed")
        return True
