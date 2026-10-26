"""Small statistics for comparing two runs, and how a share is written. Standard library only.

The dashboard and the case study use the same rules, so a change gets an arrow in both or in neither:

- Time per document is compared with a rank test (Mann-Whitney U, normal approximation with a tie correction),
  because the typical time shown is a median and the times have a long right tail.
- The other measures are averages per document (fields right, made-up values, fields wrongly left blank,
  quotes thrown out, cost), compared with Welch's t-test. The document is the unit, so the ten fields of one
  document are not counted as ten independent tries.
- The six headline numbers are judged together with Holm's step-down correction, so when nothing has changed
  between two runs, the chance of even one false call among the six is at most 5%. A number whose test does not
  clear its Holm threshold is no clear change.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

ALPHA = 0.05


def fixed(x: float, places: int) -> str:
    """x to `places` decimals the way JavaScript's toFixed does it: the exact stored value, halves rounded up.
    The case study and the Dash app then show the same digits; Python's own format rounds halves to even."""
    if x < 0:
        return "-" + fixed(-x, places)
    return str(Decimal(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def pct_label(v: float, places: int | None = None) -> str:
    """A share as a person reads it. 100% only when everything was right and 0% only when nothing was, so a
    value just under 100% is never rounded up to it: whole percents, one decimal below 10% and above 99%.
    With `places`, every share gets that many decimals, as in a table column, under the same two rules."""
    if places is not None:
        step = 10.0**-places
        if v >= 1 or v <= 0:
            return f"{100 if v >= 1 else 0:.{places}f}%"
        if v * 100 < step / 2:
            return f"<{step:.{places}f}%"
        shown = fixed(v * 100, places)
        return (f"{100 - step:.{places}f}" if float(shown) >= 100 else shown) + "%"
    if v >= 1:
        return "100%"
    if v <= 0:
        return "0%"
    p = v * 100
    if p < 0.05:
        return "<0.1%"
    if p < 9.95:
        return f"{fixed(p, 1)}%"
    if p > 99:
        return f"{math.floor(p * 10 + 1e-9) / 10:.1f}%"
    return f"{fixed(p, 0)}%"


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < 3e-14:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """The regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def welch_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Two-sided p-value of Welch's t-test for a difference in means."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 1.0
    m1, m2 = sum(a) / n1, sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    s1, s2 = v1 / n1, v2 / n2
    se2 = s1 + s2
    if se2 == 0:
        return 1.0 if m1 == m2 else 0.0
    t = (m2 - m1) / math.sqrt(se2)
    df = se2**2 / (s1**2 / (n1 - 1) + s2**2 / (n2 - 1))
    return _betai(df / 2, 0.5, df / (df + t * t))


def mann_whitney_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Two-sided p-value of the Mann-Whitney U test, normal approximation with tie and continuity corrections."""
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return 1.0
    pooled = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    n = n1 + n2
    r1 = ties = 0.0
    i = 0
    while i < n:
        j = i
        while j < n and pooled[j][0] == pooled[i][0]:
            j += 1
        rank = (i + j + 1) / 2
        r1 += rank * sum(1 for k in range(i, j) if pooled[k][1] == 0)
        t = j - i
        ties += t**3 - t
        i = j
    u1 = r1 - n1 * (n1 + 1) / 2
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    if var <= 0:
        return 1.0
    z = max(0.0, abs(u1 - n1 * n2 / 2) - 0.5) / math.sqrt(var)
    return 2 * (1 - _phi(z))


def p_value(a: Sequence[float], b: Sequence[float], test: str = "welch") -> float:
    """Two-sided p-value for a difference between two runs: the rank test for time, Welch's t-test otherwise."""
    return mann_whitney_p(a, b) if test == "rank" else welch_p(a, b)


def clear_change(a: Sequence[float], b: Sequence[float], test: str = "welch") -> bool:
    """Whether two runs differ by more than run-to-run noise, at 95% confidence, for one number on its own."""
    return p_value(a, b, test) < ALPHA


def holm(pvalues: Sequence[float], alpha: float = ALPHA) -> list[bool]:
    """Which of several tests hold up under Holm's step-down correction, in the order given.

    The smallest p-value must beat alpha / m, the next alpha / (m - 1), and so on; the first one that misses
    stops the rest. Taken together, the chance of even one false call when nothing changed is at most alpha.
    """
    m = len(pvalues)
    called = [False] * m
    for rank, i in enumerate(sorted(range(m), key=lambda k: pvalues[k])):
        if pvalues[i] >= alpha / (m - rank):
            break
        called[i] = True
    return called
