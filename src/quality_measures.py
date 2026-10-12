from scipy.stats import ks_2samp
import math

def mean_quality(subgroup_values, reference_values):
    """Measure the absolute difference between two groups' means."""
    if len(subgroup_values) == 0 or len(reference_values) == 0:
        raise ValueError("Both groups must contain at least one value.")

    subgroup_mean = sum(subgroup_values) / len(subgroup_values)
    reference_mean = sum(reference_values) / len(reference_values)

    return abs(subgroup_mean - reference_mean)


def ks_quality(subgroup_values, reference_values):
    """Compare two rating-growth distributions using a size-adjusted KS score."""
    if len(subgroup_values) == 0 or len(reference_values) == 0:
        raise ValueError("Both groups must contain at least one value.")

    ks_statistic = ks_2samp(subgroup_values, reference_values).statistic

    subgroup_size = len(subgroup_values)
    reference_size = len(reference_values)

    size_adjustment = math.sqrt(
        subgroup_size * reference_size / (subgroup_size + reference_size)
    )

    return ks_statistic * size_adjustment