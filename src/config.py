"""Shared paths and constants."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GENERATED_DIR = DATA_DIR / "generated"

GAMES_FILE = RAW_DIR / "dataset.csv"
PROFILES_FILE = RAW_DIR / "player_profiles.csv"
RATING_HISTORY_FILE = RAW_DIR / "player_rating_history.csv"

 # one row per core player
PLAYERS_TABLE = PROCESSED_DIR / "players.csv"  

# Standard time controls we keep (ultraBullet and variants are excluded for now).
TIME_CONTROLS = ["bullet", "blitz", "rapid", "classical"]

# Players need at least this many rated games in their main time control
# (taken from the profile totals, not the sampled games).
MIN_GAMES_MAIN_TC = 50

# Games shorter than this many half-moves are treated as aborted.
MIN_TURNS = 4

GROWTH_WINDOWS_MONTHS = [1, 3, 6]

# A player's rating at the start of a growth window is only trusted if they had
# at least this many days with rating changes (in that time control) before it.
MIN_HISTORY_DAYS_BEFORE_WINDOW = 10

# Opponents: players who appear in the games but weren't crawled themselves.
OPPONENT_PROFILES_FILE = RAW_DIR / "opponent_profiles.csv"
OPPONENT_RATING_HISTORY_FILES = [
    RAW_DIR / "opponent_rating_history_part1.zip",
    RAW_DIR / "opponent_rating_history_part2.zip",
]

# one row per player (core players + opponents), profile/history-based columns only
PLAYERS_ALL_TABLE = PROCESSED_DIR / "players_all.csv"

# For players_all, the main time control is the one with the most rating changes
# in this many months before the reference date (opponents have ~1 sampled game).
MAIN_TC_RECENT_MONTHS = 3

# one row per pair of players who played each other (built by src/edges.py)
EDGES_ALL_TABLE = PROCESSED_DIR / "edges_all.csv"    # nodes = players_all.csv
EDGES_CORE_TABLE = PROCESSED_DIR / "edges_core.csv"  # nodes = players.csv (core only)

# One fixed date for account age, growth windows and which games count: the day of
# the most recent game in the original crawl. Games played after it are ignored.
REFERENCE_DATE = pd.Timestamp("2026-10-07")

# Snowball step: the games, profiles and rating history of ~200 opponents who were
# crawled as well, so the network gets opponent-opponent edges.
SNOWBALL_GAMES_FILE = RAW_DIR / "additional_opponent_games.csv"
SNOWBALL_PROFILES_FILE = RAW_DIR / "200opponent_profiles.csv"
SNOWBALL_RATING_HISTORY_FILE = RAW_DIR / "200opponent_rating_history.csv"

# Snowball players are described by their most recent games before the reference
# date, at most this many (same as the core players), and need at least
# MIN_SAMPLED_GAMES of them to be included.
SAMPLED_GAMES_PER_PLAYER = 50
MIN_SAMPLED_GAMES = 20

# core + snowball players, same columns as players.csv
PLAYERS_SNOWBALL_TABLE = PROCESSED_DIR / "players_snowball.csv"
# edges from the original + snowball games
EDGES_SNOWBALL_TABLE = PROCESSED_DIR / "edges_snowball.csv"            # nodes = players_all.csv
EDGES_SNOWBALL_CORE_TABLE = PROCESSED_DIR / "edges_snowball_core.csv"  # nodes = players_snowball.csv

# generated data
PLAYERS_GENERATED_TABLE = GENERATED_DIR / "players.csv"
EDGES_GENERATED_TABLE = GENERATED_DIR / "edges.csv"

# Local subgroup discovery on the player network (src/network_mining.py).
# Each dataset bundles its two tables, its target and the role of its columns.
# To mine a different dataset, change NETWORK_DATASET below; network_mining.py
# reads everything else from the entry it points to.
NETWORK_DATASETS = {
    "snowball": {
        "players": PLAYERS_SNOWBALL_TABLE,
        "edges": EDGES_SNOWBALL_CORE_TABLE,
        "target": "target_growth_3m",
        "categorical_columns": ["title", "main_tc"],
        "columns_to_ignore": [
            "username", "rating",
            "target_growth_games",
            "target_growth_1m", "target_growth_1m_top20",
            "target_growth_3m", "target_growth_3m_top20",
            "target_growth_6m", "target_growth_6m_top20",
        ],
    },
    "generated": {
        "players": PLAYERS_GENERATED_TABLE,
        "edges": EDGES_GENERATED_TABLE,
        "target": "target",
        "categorical_columns": ["title", "main_tc"],
        "columns_to_ignore": ["id", "rating", "target", "group", "WKL_target_bin"],
    },
}

NETWORK_DATASET = "generated"   # which NETWORK_DATASETS entry to mine
NETWORK_TOP_GROUPS = 20         # number of top subgroups to return
