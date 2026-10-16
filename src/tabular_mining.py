
"""Tabular subgroup discovery for numerical rating-growth targets."""

from itertools import combinations

import numpy as np
import pandas as pd

from src import config
from src.quality_measures import mean_quality, ks_quality
from statsmodels.stats.multitest import multipletests


TARGETS = [
    "target_growth_games",
    "target_growth_1m",
    "target_growth_3m",
    "target_growth_6m",
]

# These columns identify players or contain target information,
# so they must not be used to describe subgroups.
EXCLUDED_COLUMNS = {
    "username",
    "is_snowball",
    "n_games",
    "rating",
    "target_growth_games",
    "target_growth_1m",
    "target_growth_1m_top20",
    "target_growth_3m",
    "target_growth_3m_top20",
    "target_growth_6m",
    "target_growth_6m_top20",
}


def load_players(target="target_growth_3m"):
    """Load snowball players with an observed numerical target."""
    df = pd.read_csv(config.PLAYERS_SNOWBALL_TABLE)

    if target not in df.columns:
        raise ValueError(f"Target column not found: {target}")

    return df.dropna(subset=[target]).copy()


def make_selectors(df):
    """Create candidate conditions from player characteristics."""
    selectors = []

    for column in df.columns:
        if column in EXCLUDED_COLUMNS:
            continue

        series = df[column].dropna()

        if pd.api.types.is_numeric_dtype(series):
            thresholds = series.quantile([0.25, 0.5, 0.75]).unique()

            for threshold in thresholds:
                le_mask = series <= threshold
                gt_mask = series > threshold

                if le_mask.any() and not le_mask.all():
                    selectors.append((column, "<=", float(threshold)))

                if gt_mask.any() and not gt_mask.all():
                    selectors.append((column, ">", float(threshold)))
        else:
            for value in series.unique():
                mask = series == value

                if mask.any() and not mask.all():
                    selectors.append((column, "=", value))

    return selectors


def apply_selector(df, selector):
    """Return a mask identifying rows that satisfy one condition."""
    column, operator, value = selector

    if operator == "<=":
        return df[column] <= value
    if operator == ">":
        return df[column] > value
    return df[column] == value


def describe_selector(selector):
    """Convert a condition into readable text."""
    column, operator, value = selector

    if isinstance(value, (float, np.floating)):
        value = round(value, 3)

    return f"{column} {operator} {value}"


def mine_subgroups(
    quality="mean",
    target="target_growth_3m",
    min_size=5,
    max_depth=2,
    top_k=10,
    _df=None,
):
    """Find subgroups with unusual numerical target values."""
    if min_size < 1:
        raise ValueError("min_size must be at least 1")
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    df = (
    load_players(target)
    if _df is None
    else _df.copy())

    if quality == "mean":
        quality_function = mean_quality
    elif quality == "ks":
        quality_function = ks_quality
    else:
        raise ValueError("quality must be 'mean' or 'ks'")

    selectors = make_selectors(df)
    results = []

    for depth in range(1, max_depth + 1):
        for subgroup in combinations(selectors, depth):
            columns = [selector[0] for selector in subgroup]

            if len(set(columns)) != len(columns):
                continue

            mask = pd.Series(True, index=df.index)

            for selector in subgroup:
                mask &= apply_selector(df, selector).fillna(False)

            subgroup_df = df.loc[mask]
            reference_df = df.loc[~mask]

            if len(subgroup_df) < min_size or reference_df.empty:
                continue

            subgroup_values = subgroup_df[target].to_numpy()
            reference_values = reference_df[target].to_numpy()

            score = quality_function(subgroup_values, reference_values)

            results.append({
                "target": target,
                "quality": quality,
                "description": " AND ".join(
                    describe_selector(selector)
                    for selector in subgroup
                ),
                "size": len(subgroup_df),
                "score": score,
                "subgroup_mean": subgroup_values.mean(),
                "reference_mean": reference_values.mean(),
            })

    results.sort(key=lambda result: result["score"], reverse=True)
    return pd.DataFrame(results[:top_k])


def mine_all_targets(
    min_size=5,
    max_depth=2,
    top_k=10,
):
    """Mine all numerical targets using both quality measures."""
    results = []

    for target in TARGETS:
        for quality in ["mean", "ks"]:
            result = mine_subgroups(
                quality=quality,
                target=target,
                min_size=min_size,
                max_depth=max_depth,
                top_k=top_k,
            )
            results.append(result)

    return pd.concat(results, ignore_index=True)



def permutation_test(
    target="target_growth_3m",
    quality="mean",
    n_permutations=20,
    random_state=42,
    min_size=5,
    max_depth=2,
):
    """Test the strongest subgroup using target permutations."""
    if n_permutations < 1:
        raise ValueError("n_permutations must be at least 1")
    if min_size < 1 or max_depth < 1:
        raise ValueError("min_size and max_depth must be positive")
    if quality not in {"mean", "ks"}:
        raise ValueError("quality must be 'mean' or 'ks'")

    df = load_players(target).reset_index(drop=True)
    selectors = make_selectors(df)
    n_rows = len(df)

    if quality == "mean":
        quality_function = mean_quality
    else:
        quality_function = ks_quality

    # Calculate each candidate subgroup's membership only once.
    subgroup_masks = []

    for depth in range(1, max_depth + 1):
        for subgroup in combinations(selectors, depth):
            columns = [selector[0] for selector in subgroup]

            if len(set(columns)) != len(columns):
                continue

            mask = np.ones(n_rows, dtype=bool)

            for selector in subgroup:
                selector_mask = (
                    apply_selector(df, selector)
                    .fillna(False)
                    .to_numpy(dtype=bool)
                )
                mask &= selector_mask

            size = int(mask.sum())

            if size < min_size or size == n_rows:
                continue

            subgroup_masks.append(mask)

    if not subgroup_masks:
        raise ValueError("No valid subgroups found")

    target_values = df[target].to_numpy()
    observed_score = max(
        quality_function(target_values[mask], target_values[~mask])
        for mask in subgroup_masks
    )

    rng = np.random.default_rng(random_state)
    null_scores = []

    for permutation in range(n_permutations):
        shuffled_values = rng.permutation(target_values)

        max_score = max(
            quality_function(
                shuffled_values[mask],
                shuffled_values[~mask],
            )
            for mask in subgroup_masks
        )
        null_scores.append(max_score)

        if (permutation + 1) % 25 == 0 or permutation + 1 == n_permutations:
            print(
                f"  {target} / {quality}: "
                f"{permutation + 1}/{n_permutations} permutations",
                flush=True,
            )

    p_value = (
        1 + sum(score >= observed_score for score in null_scores)
    ) / (n_permutations + 1)

    return {
        "target": target,
        "quality": quality,
        "observed_score": observed_score,
        "p_value": p_value,
        "n_permutations": n_permutations,
        "null_scores": null_scores,
    }


def permutation_test_all_targets(
    n_permutations=500,
    random_state=42,
    min_size=5,
    max_depth=2,
    output_path=None,
):
    """Run permutation tests for every target and quality measure."""
    from statsmodels.stats.multitest import multipletests

    results = []
    total = len(TARGETS) * 2
    completed = 0

    for i, target in enumerate(TARGETS):
        for quality in ["mean", "ks"]:
            print(
                f"[{completed + 1}/{total}] "
                f"Testing {target} with {quality} quality "
                f"({n_permutations} permutations)...",
                flush=True,
            )

            result = permutation_test(
                target=target,
                quality=quality,
                n_permutations=n_permutations,
                random_state=random_state + i * 2 + (quality == "ks"),
                min_size=min_size,
                max_depth=max_depth,
            )

            results.append({
                "target": result["target"],
                "quality": result["quality"],
                "observed_score": result["observed_score"],
                "p_value": result["p_value"],
                "n_permutations": result["n_permutations"],
            })

            completed += 1

    results_df = pd.DataFrame(results)

    results_df["holm_adjusted_p_value"] = multipletests(
        results_df["p_value"],
        method="holm",
    )[1]

    if output_path is not None:
        results_df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}", flush=True)

    return results_df


if __name__ == "__main__":
    results = mine_all_targets()
    print(results.to_string(index=False))