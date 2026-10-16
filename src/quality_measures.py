from scipy.stats import ks_2samp
import math

def mean_quality(subgroup_values, reference_values):
    """Measure the size-adjusted difference between two groups' means."""
    if len(subgroup_values) == 0 or len(reference_values) == 0:
        raise ValueError("Both groups must contain at least one value.")

    subgroup_mean = sum(subgroup_values) / len(subgroup_values)
    reference_mean = sum(reference_values) / len(reference_values)

    size_adjustment = math.sqrt(
        len(subgroup_values) * len(reference_values)
        / (len(subgroup_values) + len(reference_values))
    )

    return abs(subgroup_mean - reference_mean) * size_adjustment



def wracc_quality(subgroup_values, reference_values):
    """WRAcc between a subgroup and the whole population."""
    if len(subgroup_values) == 0 or len(reference_values) == 0:
        return 0

    cover = len(subgroup_values) / len(reference_values)
    subgroup_mean = sum(subgroup_values) / len(subgroup_values)
    reference_mean = sum(reference_values) / len(reference_values)

    return abs((cover ** 0.5) * (subgroup_mean - reference_mean))



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


# the measures that can be picked from the config (see NETWORK_QUALITY_MEASURE)
QUALITY_MEASURES = {
    "ks": ks_quality,
    "wracc": wracc_quality,
    "mean": mean_quality,
}


def get_quality_measure(name):
    """Look up a quality measure by name (see QUALITY_MEASURES)."""
    try:
        return QUALITY_MEASURES[name]
    except KeyError:
        raise ValueError(
            f"Unknown quality measure {name!r}; choose from {sorted(QUALITY_MEASURES)}"
        )
