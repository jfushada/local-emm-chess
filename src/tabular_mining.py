
"""Tabular subgroup discovery for numerical rating-growth targets."""

from itertools import combinations

import numpy as np
import pandas as pd

from src import config
from src.quality_measures import mean_quality, ks_quality


TARGET = "target_growth_3m"

# These columns identify players or contain target information,
# so they must not be used to describe subgroups.
EXCLUDED_COLUMNS = {
    "username",
    "target_growth_games",
    "target_growth_1m",
    "target_growth_1m_top20",
    "target_growth_3m",
    "target_growth_3m_top20",
    "target_growth_6m",
    "target_growth_6m_top20",
}


def load_players():
    """Load players with an observed numerical target."""
    df = pd.read_csv(config.PLAYERS_TABLE)
    return df.dropna(subset=[TARGET]).copy()


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
                selectors.append(
                    (column, "<=", float(threshold))
                )
                selectors.append(
                    (column, ">", float(threshold))
                )
        else:
            for value in series.unique():
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


def mine_subgroups(quality="mean", min_size=5, max_depth=2, top_k=10,):
    """Find player subgroups with unusual three-month rating growth."""
    if min_size < 1:
        raise ValueError("min_size must be at least 1")
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    df = load_players()

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
            # Avoid combining conditions on the same feature.
            columns = [selector[0] for selector in subgroup]
            if len(set(columns)) != len(columns):
                continue

            mask = pd.Series(True, index=df.index)

            for selector in subgroup:
                mask &= apply_selector(df, selector).fillna(False)

            mask = mask.fillna(False)
            subgroup_df = df.loc[mask]

            if len(subgroup_df) < min_size:
                continue

            subgroup_values = subgroup_df[TARGET].to_numpy()
            reference = df.loc[~mask, TARGET].to_numpy()

            if len(reference) == 0:
                continue

            score = quality_function(subgroup_values, reference)

            results.append({
                "description": " AND ".join(
                    describe_selector(selector)
                    for selector in subgroup
                ),
                "size": len(subgroup_df),
                "score": score,
                "subgroup_mean": subgroup_values.mean(),
                "reference_mean": reference.mean(),
            })

    results.sort(key=lambda result: result["score"], reverse=True)
    return pd.DataFrame(results[:top_k])


if __name__ == "__main__":
    print("Top subgroups using mean-based quality:")
    print(mine_subgroups(quality="mean").to_string(index=False))

    print("\nTop subgroups using KS-based quality:")
    print(mine_subgroups(quality="ks").to_string(index=False))
