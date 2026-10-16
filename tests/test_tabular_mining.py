
import pandas as pd
import pytest
from src import tabular_mining


def test_load_players_excludes_missing_targets(monkeypatch):
    df = pd.DataFrame({
        "username": ["a", "b", "c"],
        "target_growth_3m": [10.0, None, -5.0],
    })

    monkeypatch.setattr(
        tabular_mining.pd,
        "read_csv",
        lambda path: df.copy(),
    )

    result = tabular_mining.load_players()

    assert len(result) == 2
    assert result["target_growth_3m"].isna().sum() == 0


def test_target_columns_are_excluded():
    df = pd.DataFrame({
        "win_rate": [0.4, 0.5, 0.6],
        "target_growth_3m": [10, 20, 30],
        "target_growth_3m_top20": [1, 0, 1],
    })

    selectors = tabular_mining.make_selectors(df)
    columns = {selector[0] for selector in selectors}

    assert "win_rate" in columns
    assert "target_growth_3m" not in columns
    assert "target_growth_3m_top20" not in columns


def test_mine_subgroups_returns_results(monkeypatch):
    df = pd.DataFrame({
        "win_rate": [0.1, 0.2, 0.3, 0.8, 0.9, 1.0],
        "target_growth_3m": [100, 90, 80, 0, -10, -20],
    })

    monkeypatch.setattr(
        tabular_mining,
        "load_players",
        lambda target="target_growth_3m": df.copy(),
    )

    result = tabular_mining.mine_subgroups(
        quality="mean",
        min_size=2,
        max_depth=1,
        top_k=3,
    )

    assert not result.empty
    assert len(result) <= 3
    assert {"description", "size", "score"}.issubset(result.columns)
    assert result["score"].is_monotonic_decreasing


def test_mine_subgroups_supports_ks(monkeypatch):
    df = pd.DataFrame({
        "win_rate": [0.1, 0.2, 0.3, 0.8, 0.9, 1.0],
        "target_growth_3m": [100, 90, 80, 0, -10, -20],
    })

    monkeypatch.setattr(
        tabular_mining,
        "load_players",
        lambda target="target_growth_3m": df.copy(),
    )

    result = tabular_mining.mine_subgroups(
        quality="ks",
        min_size=2,
        max_depth=1,
        top_k=3,
    )

    assert not result.empty



def test_invalid_quality_raises_error(monkeypatch):
    monkeypatch.setattr(
        tabular_mining,
        "load_players",
        lambda target="target_growth_3m": pd.DataFrame({
            "win_rate": [0.1, 0.2],
            "target_growth_3m": [10, 20],
        }),
    )

    with pytest.raises(ValueError):
        tabular_mining.mine_subgroups(quality="invalid")



def test_make_selectors_skips_conditions_matching_all_or_no_players():
    """Selectors should meaningfully filter the player dataset."""
    df = pd.DataFrame({
        "share_blitz": [1.0, 1.0, 1.0],
        "share_rapid": [0.0, 0.5, 1.0],
    })

    selectors = tabular_mining.make_selectors(df)
    # A constant column should not produce any selectors.
    assert all(column != "share_blitz" for column, _, *_ in selectors)
    # A varying column should still produce candidate selectors.
    assert any(column == "share_rapid" for column, _, *_ in selectors)



def test_permutation_test_returns_expected_results(monkeypatch):
    df = pd.DataFrame({
        "win_rate": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "target_growth_3m": [10, 20, 30, 40, 50, 60],
    })

    monkeypatch.setattr(
        tabular_mining,
        "load_players",
        lambda target="target_growth_3m": df.copy(),
    )

    result = tabular_mining.permutation_test(
        n_permutations=3,
        min_size=1,
        max_depth=1,
    )

    assert result["target"] == "target_growth_3m"
    assert result["quality"] == "mean"
    assert 0 <= result["p_value"] <= 1
    assert len(result["null_scores"]) == 3
    assert result["n_permutations"] == 3


def test_permutation_test_is_reproducible(monkeypatch):
    df = pd.DataFrame({
        "win_rate": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "target_growth_3m": [10, 20, 30, 40, 50, 60],
    })

    monkeypatch.setattr(
        tabular_mining,
        "load_players",
        lambda target="target_growth_3m": df.copy(),
    )

    first = tabular_mining.permutation_test(
        n_permutations=3,
        random_state=42,
        min_size=1,
        max_depth=1,
    )

    second = tabular_mining.permutation_test(
        n_permutations=3,
        random_state=42,
        min_size=1,
        max_depth=1,
    )

    assert first["observed_score"] == second["observed_score"]
    assert first["p_value"] == second["p_value"]
    assert first["null_scores"] == second["null_scores"]


def test_permutation_test_rejects_invalid_count():
    with pytest.raises(ValueError):
        tabular_mining.permutation_test(n_permutations=0)