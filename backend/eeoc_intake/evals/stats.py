########################################################################
#                  backend/eeoc_intake/evals/stats.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Small statistics for comparing two runs, and how #
#                     a share is written. Standard library only.       #
########################################################################
"""Tests for a change between two runs, and how a share is written.

The dashboard and the case study use the same rules, so a change gets
an arrow in both or in neither:

- Time per document is compared with a rank test (Mann-Whitney U,
  normal approximation with a tie correction), because the typical
  time shown is a median and the times have a long right tail.
- The other measures are averages per document (fields right, made-up
  values, fields wrongly left blank, quotes thrown out, cost), compared
  with Welch's t-test. The document is the unit, so the ten fields of
  one document are not counted as ten independent tries.
- The six headline numbers are judged together with Holm's step-down
  correction, so when nothing has changed between two runs, the chance
  of even one false call among the six is at most 5%.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from kds.logs import get_logger

# Module constants
log = get_logger(__name__)
# log.debug("Sets the chance of a false call the tests allow")
ALPHA: Final = 0.05
# log.debug("Names the rank test, used for time")
RANK: Final = "rank"
# log.debug("Names the t-test, used for every average")
WELCH: Final = "welch"
# log.debug("Sets the percent a share of one is")
PERCENT: Final = 100
# log.debug("Sets the smallest percent shown as a number; below it reads under 0.1")
SMALLEST_SHOWN: Final = 0.05
# log.debug("Sets the percent below which one decimal is shown")
TENTHS_BELOW: Final = 9.95
# log.debug("Sets the percent above which one decimal is shown, rounded down")
TENTHS_ABOVE: Final = 99
# log.debug("Sets the base of the decimals a share is written in")
DECIMAL: Final = 10
# log.debug("Sets one half, used by rounding and the tests' corrections")
HALF: Final = 0.5
# log.debug("Sets the nudge that keeps a float like 99.9 from flooring to 99.8")
NUDGE: Final = 1e-9
# log.debug("Sets the smallest number the continued fraction divides by")
TINY: Final = 1e-300
# log.debug("Sets the most terms the continued fraction sums")
MAX_TERMS: Final = 300
# log.debug("Sets how close to one a term must be to stop early")
CONVERGED: Final = 3e-14
# log.debug("Sets the fewest values a sample needs for a variance")
MIN_SAMPLE: Final = 2


# log.debug("Defines rounding the way JavaScript's toFixed does it")
def fixed(x: float, places: int) -> str:
    """Return x to `places` decimals, halves rounded up, like toFixed.

    The exact stored value is rounded, so the case study and the
    dashboard show the same digits; Python's own format rounds halves
    to even.
    """
    # log.debug("Rounds a negative number as its opposite, with a minus sign")
    if x < 0:
        # log.debug("Returns the minus sign and the rounded opposite")
        return "-" + fixed(-x, places)
    # log.debug("Returns the exact value rounded half up to the places asked")
    return str(Decimal(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


# log.debug("Defines how a share is written")
def pct_label(v: float, places: int | None = None) -> str:
    """Return a share as a person reads it.

    100% only when everything was right and 0% only when nothing was,
    so a value just under 100% is never rounded up to it: whole
    percents, one decimal below 10% and above 99%. With `places`, every
    share gets that many decimals, as in a table column, under the same
    two rules.
    """
    # log.debug("Writes a table column's share with its fixed decimals")
    if places is not None:
        # log.debug("Returns the column form")
        return _column(v, places)
    # log.debug("Writes all right as a hundred percent and none right as zero")
    if v >= 1 or v <= 0:
        # log.debug("Returns a hundred or zero percent")
        return "100%" if v >= 1 else "0%"
    # log.debug("Returns the share written as a percent")
    return _percent(v * PERCENT)


# log.debug("Defines a percent strictly between 0 and 100, as written")
def _percent(p: float) -> str:
    """Return p with the decimals its size calls for."""
    # log.debug("Writes a tiny share as under a tenth of a percent, never as zero")
    if p < SMALLEST_SHOWN:
        # log.debug("Returns under a tenth of a percent")
        return "<0.1%"
    # log.debug("Writes a share under ten percent with one decimal")
    if p < TENTHS_BELOW:
        # log.debug("Returns one decimal")
        return f"{fixed(p, 1)}%"
    # log.debug("Writes a share over 99 percent with one decimal, rounded down")
    if p > TENTHS_ABOVE:
        # log.debug("Returns one decimal, never rounded up to a hundred")
        return f"{math.floor(p * DECIMAL + NUDGE) / DECIMAL:.1f}%"
    # log.debug("Returns a whole percent")
    return f"{fixed(p, 0)}%"


# log.debug("Defines a share with a fixed number of decimals")
def _column(v: float, places: int) -> str:
    """Return a share with `places` decimals, never rounded to 0 or 100.

    Used for table columns, where every share has the same decimals.
    """
    # log.debug("Finds the smallest step those decimals can show")
    step = float(DECIMAL) ** -places
    # log.debug("Writes all or none right exactly")
    if v >= 1 or v <= 0:
        # log.debug("Returns 100 or 0 with the decimals")
        return f"{PERCENT if v >= 1 else 0:.{places}f}%"
    # log.debug("Writes a share smaller than half a step as under one step")
    if v * PERCENT < step * HALF:
        # log.debug("Returns under one step")
        return f"<{step:.{places}f}%"
    # log.debug("Rounds the percent half up")
    shown = fixed(v * PERCENT, places)
    # log.debug("Returns it, held one step under 100 when it would round up")
    return (f"{PERCENT - step:.{places}f}" if float(shown) >= PERCENT else shown) + "%"


# log.debug("Defines the standard normal distribution function")
def _phi(z: float) -> float:
    """Return the chance a standard normal value is at most z."""
    # log.debug("Returns it through the error function")
    return HALF * (1 + math.erf(z / math.sqrt(2)))


# log.debug("Defines a guard against dividing by almost zero")
def _safe(x: float) -> float:
    """Return x, or TINY when x is closer to zero than TINY."""
    # log.debug("Returns x when it is far enough from zero")
    return x if abs(x) > TINY else TINY


# log.debug("Defines the continued fraction for the incomplete beta function")
def _betacf(a: float, b: float, x: float) -> float:
    """Return the continued fraction, by the modified Lentz method."""
    # log.debug("Precomputes the sums the terms use")
    qab, qap, qam = a + b, a + 1, a - 1
    # log.debug("Starts the two running ratios")
    c, d = 1.0, 1.0 / _safe(1.0 - qab * x / qap)
    # log.debug("Starts the product at the first term")
    h = d
    # log.debug("Adds two terms per step until they stop changing it")
    for m in range(1, MAX_TERMS):
        # log.debug("Doubles the step number, which both terms use")
        m2 = 2 * m
        # log.debug("Computes the even term")
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        # log.debug("Updates the denominator ratio")
        d = 1.0 / _safe(1.0 + aa * d)
        # log.debug("Updates the numerator ratio")
        c = _safe(1.0 + aa / c)
        # log.debug("Folds the even term into the product")
        h *= d * c
        # log.debug("Computes the odd term")
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        # log.debug("Updates the denominator ratio")
        d = 1.0 / _safe(1.0 + aa * d)
        # log.debug("Updates the numerator ratio")
        c = _safe(1.0 + aa / c)
        # log.debug("Computes the odd term's factor")
        de = d * c
        # log.debug("Folds it into the product")
        h *= de
        # log.debug("Stops once a step no longer changes the product")
        if abs(de - 1.0) < CONVERGED:
            # log.debug("Leaves the loop")
            break
    # log.debug("Returns the product")
    return h


# log.debug("Defines the regularized incomplete beta function")
def _betai(a: float, b: float, x: float) -> float:
    """Return I_x(a, b)."""
    # log.debug("Returns zero at or below the start")
    if x <= 0:
        # log.debug("Returns zero")
        return 0.0
    # log.debug("Returns one at or past the end")
    if x >= 1:
        # log.debug("Returns one")
        return 1.0
    # log.debug("Computes the factor in front of the continued fraction")
    front = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1 - x)
    )
    # log.debug("Uses the fraction directly where it converges fast")
    if x < (a + 1) / (a + b + 2):
        # log.debug("Returns the direct form")
        return front * _betacf(a, b, x) / a
    # log.debug("Returns the mirrored form elsewhere")
    return 1.0 - front * _betacf(b, a, 1 - x) / b


# log.debug("Defines Welch's t-test")
def welch_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the two-sided p-value of Welch's t-test on the means."""
    # log.debug("Counts each sample")
    n1, n2 = len(a), len(b)
    # log.debug("Calls a sample too small for a variance no evidence of change")
    if n1 < MIN_SAMPLE or n2 < MIN_SAMPLE:
        # log.debug("Returns no evidence")
        return 1.0
    # log.debug("Computes each mean")
    m1, m2 = sum(a) / n1, sum(b) / n2
    # log.debug("Computes the first sample's variance")
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    # log.debug("Computes the second sample's variance")
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    # log.debug("Computes each mean's squared standard error")
    s1, s2 = v1 / n1, v2 / n2
    # log.debug("Adds them for the difference's")
    se2 = s1 + s2
    # log.debug("Handles two samples with no spread at all")
    if se2 == 0:
        # log.debug("Returns certainty of a change only when the means differ")
        return 1.0 if m1 == m2 else 0.0
    # log.debug("Computes the t statistic")
    t = (m2 - m1) / math.sqrt(se2)
    # log.debug("Computes the Welch-Satterthwaite degrees of freedom")
    df = se2**2 / (s1**2 / (n1 - 1) + s2**2 / (n2 - 1))
    # log.debug("Returns the two-sided tail through the incomplete beta function")
    return _betai(df / 2, HALF, df / (df + t * t))


# log.debug("Defines the Mann-Whitney U test")
def mann_whitney_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the two-sided p-value of the Mann-Whitney U test.

    Normal approximation, with tie and continuity corrections.
    """
    # log.debug("Counts each sample")
    n1, n2 = len(a), len(b)
    # log.debug("Calls an empty sample no evidence of change")
    if not n1 or not n2:
        # log.debug("Returns no evidence")
        return 1.0
    # log.debug("Sums the first sample's ranks and the tie correction")
    r1, ties = _ranks(a, b)
    # log.debug("Counts both samples together")
    n = n1 + n2
    # log.debug("Computes the first sample's U")
    u1 = r1 - n1 * (n1 + 1) / 2
    # log.debug("Computes U's variance, corrected for ties")
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    # log.debug("Calls a sample of identical values no evidence of change")
    if var <= 0:
        # log.debug("Returns no evidence")
        return 1.0
    # log.debug("Computes z with the continuity correction")
    z = max(0.0, abs(u1 - n1 * n2 / 2) - HALF) / math.sqrt(var)
    # log.debug("Returns the two-sided tail")
    return 2 * (1 - _phi(z))


# log.debug("Defines the rank sum and tie correction for two samples")
def _ranks(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Return the first sample's rank sum and the tie correction.

    The correction is the sum of t^3 - t over runs of t equal values.
    """
    # log.debug("Pools both samples, marking which each value came from")
    pooled = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    # log.debug("Counts the pool")
    n = len(pooled)
    # log.debug("Starts the rank sum and the tie correction at zero")
    r1 = ties = 0.0
    # log.debug("Starts at the smallest value")
    i = 0
    # log.debug("Walks the pool one run of equal values at a time")
    while i < n:
        # log.debug("Finds the end of this run of equal values")
        j = next((k for k in range(i, n) if pooled[k][0] != pooled[i][0]), n)
        # log.debug("Gives every value in the run the run's mean rank")
        rank = (i + j + 1) / 2
        # log.debug("Adds that rank once for each value from the first sample")
        r1 += rank * sum(1 for k in range(i, j) if pooled[k][1] == 0)
        # log.debug("Counts the run's length")
        t = j - i
        # log.debug("Adds its share of the tie correction")
        ties += t**3 - t
        # log.debug("Moves past the run")
        i = j
    # log.debug("Returns the rank sum and the correction")
    return r1, ties


# log.debug("Defines the test each measure uses")
def p_value(a: Sequence[float], b: Sequence[float], test: str = WELCH) -> float:
    """Return the two-sided p-value for a change between two runs.

    The rank test for time, Welch's t-test for everything else.
    """
    # log.debug("Returns the rank test's p-value for time, Welch's otherwise")
    return mann_whitney_p(a, b) if test == RANK else welch_p(a, b)


# log.debug("Defines one number's test on its own")
def clear_change(a: Sequence[float], b: Sequence[float], test: str = WELCH) -> bool:
    """Return whether two runs differ by more than run-to-run noise.

    At 95% confidence, for one number on its own.
    """
    # log.debug("Returns whether the p-value is under the threshold")
    return p_value(a, b, test) < ALPHA


# log.debug("Defines Holm's step-down correction")
def holm(pvalues: Sequence[float], alpha: float = ALPHA) -> list[bool]:
    """Return which of several tests hold up, in the order given.

    The smallest p-value must beat alpha / m, the next alpha / (m - 1),
    and so on; the first one that misses stops the rest. Taken together,
    the chance of even one false call when nothing changed is at most
    alpha.
    """
    # log.debug("Counts the tests")
    m = len(pvalues)
    # log.debug("Starts with no test called a change")
    called = [False] * m
    # log.debug("Walks the tests from the smallest p-value up")
    for rank, i in enumerate(sorted(range(m), key=lambda k: pvalues[k])):
        # log.debug("Stops at the first test that misses its threshold")
        if pvalues[i] >= alpha / (m - rank):
            # log.debug("Leaves the loop: no later test can be called")
            break
        # log.debug("Calls this one a change")
        called[i] = True
    # log.debug("Returns the calls in the order given")
    return called
