"""The statistics behind the tiles' arrows, and how a share is written."""

from eeoc_intake.evals.stats import clear_change, mann_whitney_p, pct_label, welch_p


def test_pct_label_never_rounds_to_all_or_nothing():
    assert pct_label(1) == "100%"
    assert pct_label(0.996) == "99.6%"
    assert pct_label(0.9999) == "99.9%"
    assert pct_label(0.3125) == "31%"
    assert pct_label(0.05) == "5.0%"
    assert pct_label(0.0004) == "<0.1%"
    assert pct_label(0) == "0%"
    assert pct_label(0.9996, 1) == "99.9%"
    assert pct_label(1, 1) == "100.0%"
    assert pct_label(0.93, 1) == "93.0%"
    assert pct_label(0.0003, 1) == "<0.1%"
    assert pct_label(0, 1) == "0.0%"


def test_welch_matches_a_worked_example():
    # Means 3 and 8, both variances 2.5, n = 5: t = -5 on 8 degrees of freedom, two-sided p = 0.00105.
    p = welch_p([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    assert abs(p - 0.00105) < 0.00002
    assert welch_p([1, 2, 3], [1, 2, 3]) == 1.0
    assert welch_p([1, 1, 1], [1, 1, 1]) == 1.0
    assert welch_p([0, 0, 0], [1, 1, 1]) == 0.0


def test_rank_test_separates_shifted_samples_only():
    slow = [4.1, 4.3, 4.2, 4.6, 4.4, 4.5, 4.2, 4.3, 4.4, 4.5, 4.6, 4.2]
    assert mann_whitney_p(slow, [x + 1 for x in slow]) < 0.001
    assert mann_whitney_p(slow, list(reversed(slow))) > 0.9
    assert clear_change(slow, [x + 1 for x in slow], "rank")
    assert not clear_change(slow, [x + 0.01 for x in slow], "rank")
