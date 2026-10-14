import pytest
from src.quality_measures import mean_quality
from src.quality_measures import ks_quality


def test_mean_quality_different_means():
    expected = abs(80 - (20 / 3)) * (3 * 3 / 6) ** 0.5
    assert mean_quality([80, 100, 60], [10, -20, 30]) == pytest.approx(expected)


def test_mean_quality_equal_means():
    assert mean_quality([10, 20, 30], [0, 20, 40]) == 0


def test_mean_quality_empty_subgroup():
    with pytest.raises(ValueError):
        mean_quality([], [10, 20])


def test_mean_quality_empty_reference():
    with pytest.raises(ValueError):
        mean_quality([10, 20], [])


def test_ks_quality_different_distributions():
    score = ks_quality([80, 90, 100], [-20, -10, 0])
    assert score > 0


def test_ks_quality_identical_distributions():
    score = ks_quality([10, 20, 30], [10, 20, 30])
    assert score == 0


def test_ks_quality_empty_group():
    with pytest.raises(ValueError):
        ks_quality([], [10, 20, 30])


def test_mean_quality_adjusts_for_group_size():
    subgroup = [10, 10]
    reference = [0, 0, 0]
    expected = 10 * (6 / 5) ** 0.5

    assert mean_quality(subgroup, reference) == pytest.approx(expected)
