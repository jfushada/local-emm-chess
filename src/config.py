"""Shared paths and constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

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