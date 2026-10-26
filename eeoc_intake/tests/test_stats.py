"""The statistics behind the tiles' arrows, and how a share is written."""

from eeoc_intake.evals.stats import clear_change, fixed, holm, mann_whitney_p, pct_label, welch_p


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


def test_fixed_rounds_halves_up_like_the_browser():
    # Python's own format would give 0.12 and 12; toFixed and Tableau give 0.13 and 13.
    assert fixed(0.125, 2) == "0.13"
    assert fixed(12.5, 0) == "13"
    assert fixed(-0.125, 2) == "-0.13"
    assert fixed(2.675, 2) == "2.67"  # 2.675 is stored as 2.67499..., in every language
    assert fixed(0.0134, 4) == "0.0134"
    assert pct_label(0.0996) == "10%"
    assert pct_label(0.0007) == "0.1%"


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


def test_holm_steps_down_and_stops_at_the_first_miss():
    # Sorted: 0.005 < 0.05/4, 0.01 < 0.05/3, then 0.03 misses 0.05/2, which stops 0.04 too.
    assert holm([0.01, 0.04, 0.03, 0.005]) == [True, False, False, True]
    # The live runs, third against second: the time's p of 0.010 misses 0.05 / 6.
    assert holm([1.0, 1.0, 1.0, 1.0, 0.0100, 0.987]) == [False] * 6
    # Second against first: fields right and fields left blank hold up; cost (0.034) misses 0.05 / 4.
    assert holm([9.6e-12, 1.0, 1.0, 9.6e-12, 0.62, 0.034]) == [True, False, False, True, False, False]
    assert holm([]) == []
