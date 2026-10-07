# Build the player table: one row per core player, with attributes and targets.

# Run from the repo root:  python -m src.features
# Output: data/processed/players.csv

import pandas as pd
from src import config

# load profiles of the crawled players (core players/network nodes)
def load_profiles() -> pd.DataFrame:
    profiles = pd.read_csv(config.PROFILES_FILE)
    profiles["username"] = profiles["username"].str.lower()
    return profiles


# load rated games in standard time controls, without very short games or duplicates
# standard time controls = [bullet", "blitz", "rapid", "classical"]
def load_games() -> pd.DataFrame:
    games = pd.read_csv(config.GAMES_FILE)
    games["white_player"] = games["white_player"].str.lower()
    games["black_player"] = games["black_player"].str.lower()

    games = games[games["speed"].isin(config.TIME_CONTROLS)]
    games = games[games["rated"]]
    games = games[games["turns"] >= config.MIN_TURNS]
    games = games.drop_duplicates(subset="game_id")
    return games.reset_index(drop=True)


# per-player view of games
# turn each game into two rows: one white one black
# every row = how did <username> do in this game?
def player_games(games: pd.DataFrame) -> pd.DataFrame:
    shared = ["game_id", "created_at", "speed", "turns", "opening"]

    white = games[shared].copy()
    white["username"] = games["white_player"]
    white["opponent"] = games["black_player"]
    white["rating"] = games["white_rating"]
    white["opponent_rating"] = games["black_rating"]
    white["won"] = games["winner"] == "white"

    black = games[shared].copy()
    black["username"] = games["black_player"]
    black["opponent"] = games["white_player"]
    black["rating"] = games["black_rating"]
    black["opponent_rating"] = games["white_rating"]
    black["won"] = games["winner"] == "black"

    rows = pd.concat([white, black], ignore_index=True)
    rows["drew"] = rows["game_id"].map(games.set_index("game_id")["winner"].isna())
    return rows

# attributes
def win_rate(pg: pd.DataFrame) -> pd.Series:
    """Share of games won, per player."""
    return pg.groupby("username")["won"].mean().rename("win_rate")

def draw_rate(pg: pd.DataFrame) -> pd.Series:
    """Share of games drawn, per player."""
    return pg.groupby("username")["drew"].mean().rename("draw_rate")

def avg_moves(pg: pd.DataFrame) -> pd.Series:
    """Average game length in moves (turns are half-moves)."""
    return (pg.groupby("username")["turns"].mean() / 2).rename("avg_moves")

def time_control_shares(pg: pd.DataFrame) -> pd.DataFrame:
    """Share of each player's games in each time control (rows sum to 1)."""
    shares = pd.crosstab(pg["username"], pg["speed"], normalize="index")
    shares = shares.reindex(columns=config.TIME_CONTROLS, fill_value=0)
    return shares.add_prefix("share_")

# build and save player table
def build_player_table() -> pd.DataFrame:
    profiles = load_profiles()
    games = load_games()
    pg = player_games(games)

    # Only keep rows for our core players (games against opponents still count).
    core = set(profiles["username"])
    pg = pg[pg["username"].isin(core)]

    players = pd.DataFrame(index=sorted(core))
    players.index.name = "username"
    players = players.join(pg.groupby("username").size().rename("n_games"))
    players = players.join(win_rate(pg))
    players = players.join(avg_moves(pg))
    players = players.join(draw_rate(pg))
    players = players.join(time_control_shares(pg))
    return players.reset_index()


if __name__ == "__main__":
    table = build_player_table()
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.PLAYERS_TABLE, index=False)
    print(f"Saved {len(table)} players to {config.PLAYERS_TABLE}")
    print(table.head())