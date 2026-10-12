
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
        lambda: df.copy(),
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
        lambda: df.copy(),
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
        lambda: pd.DataFrame({
            "win_rate": [0.1, 0.2],
            "target_growth_3m": [10, 20],
        }),
    )

    with pytest.raises(ValueError):
        tabular_mining.mine_subgroups(quality="invalid")
