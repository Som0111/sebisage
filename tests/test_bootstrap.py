import pytest

from sebisage.eval.bootstrap import bootstrap_ci


def test_deterministic_same_seed():
    hits = [True, False, True, True, False, True, False, False, True, True]
    first = bootstrap_ci(hits, seed=42)
    second = bootstrap_ci(hits, seed=42)
    assert first == second


def test_all_correct_gives_mean_one():
    hits = [True] * 10
    lower, upper = bootstrap_ci(hits, seed=42)
    assert lower == 1.0
    assert upper == 1.0


def test_all_wrong_gives_mean_zero():
    hits = [False] * 10
    lower, upper = bootstrap_ci(hits, seed=42)
    assert lower == 0.0
    assert upper == 0.0


def test_empty_input_raises():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_small_input_does_not_crash():
    hits = [True, False, True]
    lower, upper = bootstrap_ci(hits, seed=42)
    assert 0.0 <= lower <= upper <= 1.0
