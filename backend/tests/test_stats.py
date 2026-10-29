########################################################################
#                     backend/tests/test_stats.py                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the statistics behind the tiles' arrows, and how a share is
written.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

# Third-party
from kds.logs import get_logger

# Local
from eeoc_intake.evals.shares import fixed, pct_label
from eeoc_intake.evals.stats import clear_change, holm, mann_whitney_p, welch_p

########################################################################
#                           Global constants                           #
########################################################################
log = get_logger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets twelve times in seconds with a long right tail")
SLOW = [4.1, 4.3, 4.2, 4.6, 4.4, 4.5, 4.2, 4.3, 4.4, 4.5, 4.6, 4.2]


########################################################################
#                           Statistics tests                           #
########################################################################
# log.debug("Defines the test: a share never rounds to all or nothing")
def test_a_share_never_rounds_to_all_or_nothing() -> None:
    """Checks 100 and 0 mean all and none; the rest keep digits."""
    # log.debug("Checks whole percents and the edges")
    assert [pct_label(v) for v in (1, 0.996, 0.9999, 0.3125, 0.05, 0.0004, 0)] == [
        "100%",
        "99.6%",
        "99.9%",
        "31%",
        "5.0%",
        "<0.1%",
        "0%",
    ]
    # log.debug("Checks the column form with one decimal")
    assert [pct_label(v, 1) for v in (0.9996, 1, 0.93, 0.0003, 0)] == [
        "99.9%",
        "100.0%",
        "93.0%",
        "<0.1%",
        "0.0%",
    ]


# log.debug("Defines the test: rounding takes halves up like the browser")
def test_rounding_takes_halves_up_like_the_browser() -> None:
    """Checks halves round up, as toFixed and Tableau round them."""
    # log.debug("Checks halves round up, and negative numbers mirror them")
    assert [fixed(0.125, 2), fixed(12.5, 0), fixed(-0.125, 2)] == ["0.13", "13", "-0.13"]
    # log.debug("Checks 2.675, stored as 2.67499..., rounds down in every language")
    assert fixed(2.675, 2) == "2.67"
    # log.debug("Checks small shares around the one-decimal edge")
    assert [fixed(0.0134, 4), pct_label(0.0996), pct_label(0.0007)] == ["0.0134", "10%", "0.1%"]


# log.debug("Defines the test: welch matches a worked example")
def test_welch_matches_a_worked_example() -> None:
    """Checks Welch's t-test against a worked example."""
    # log.debug("Computes the example")
    p = welch_p([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    # log.debug("Checks it")
    assert abs(p - 0.00105) < 0.00002
    # log.debug("Checks equal samples and samples with no spread")
    assert [welch_p([1, 2, 3], [1, 2, 3]), welch_p([1, 1, 1], [1, 1, 1])] == [1.0, 1.0]
    # log.debug("Checks two different constant samples are certain")
    assert welch_p([0, 0, 0], [1, 1, 1]) == 0.0


# log.debug("Defines the test: the rank test separates shifted samples only")
def test_the_rank_test_separates_shifted_samples_only() -> None:
    """Checks a one-second shift is found, not a reorder or tiny one."""
    # log.debug("Checks a clear shift")
    assert mann_whitney_p(SLOW, [x + 1 for x in SLOW]) < 0.001
    # log.debug("Checks the same values in another order")
    assert mann_whitney_p(SLOW, list(reversed(SLOW))) > 0.9
    # log.debug("Checks the one-number call agrees")
    assert clear_change(SLOW, [x + 1 for x in SLOW], "rank")
    # log.debug("Checks a hundredth of a second is not a change")
    assert not clear_change(SLOW, [x + 0.01 for x in SLOW], "rank")


# log.debug("Defines the test: holm steps down and stops at the first miss")
def test_holm_steps_down_and_stops_at_the_first_miss() -> None:
    """Checks Holm's correction stops at the first miss."""
    # log.debug("Checks the worked example")
    assert holm([0.01, 0.04, 0.03, 0.005]) == [True, False, False, True]
    # log.debug("Checks the live runs, third against second: time's 0.010 misses")
    assert holm([1.0, 1.0, 1.0, 1.0, 0.0100, 0.987]) == [False] * 6
    # log.debug("Checks second against first: two hold up, cost's 0.034 misses")
    assert holm([9.6e-12, 1.0, 1.0, 9.6e-12, 0.62, 0.034]) == [
        True,
        False,
        False,
        True,
        False,
        False,
    ]
    # log.debug("Checks no tests give no calls")
    assert holm([]) == []
