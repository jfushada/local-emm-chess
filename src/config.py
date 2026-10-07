"""Shared paths and constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

GAMES_FILE = DATA_DIR / "dataset.csv"
PROFILES_FILE = DATA_DIR / "player_profiles.csv"
RATING_HISTORY_FILE = DATA_DIR / "player_rating_history.csv"

# Standard time controls we keep (ultraBullet and variants are excluded for now).
TIME_CONTROLS = ["bullet", "blitz", "rapid", "classical"]

# Players need at least this many rated games in their main time control
# (taken from the profile totals, not the sampled games).
MIN_GAMES_MAIN_TC = 50

# Games shorter than this many half-moves are treated as aborted.
MIN_TURNS = 4