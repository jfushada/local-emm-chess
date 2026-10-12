# Build the player tables, with attributes and targets.

# Run from the repo root:  python -m src.features
# Output:
#   data/processed/players.csv      one row per core (crawled) player, all attributes
#   data/processed/players_all.csv  core players + opponents, profile/history-based columns only

import numpy as np
import pandas as pd
from src import config

# load player profiles (default: the crawled core players)
def load_profiles(path=config.PROFILES_FILE) -> pd.DataFrame:
    profiles = pd.read_csv(path)
    profiles["username"] = profiles["username"].str.lower()
    return profiles


# load rated games in standard time controls, without very short games or duplicates
def load_games() -> pd.DataFrame:
    games = pd.read_csv(config.GAMES_FILE)
    games["white_player"] = games["white_player"].str.lower()
    games["black_player"] = games["black_player"].str.lower()

    games = games[games["speed"].isin(config.TIME_CONTROLS)]
    games = games[games["rated"]]
    games = games[games["turns"] >= config.MIN_TURNS]
    games = games.drop_duplicates(subset="game_id")
    return games.reset_index(drop=True)


# load rating history in standard time controls, one row per (player, time control, date).
# several files (e.g. the two opponent parts, which can be zipped) are combined into one
def load_rating_history(paths=(config.RATING_HISTORY_FILE,)) -> pd.DataFrame:
    history = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    history["username"] = history["username"].str.lower()
    history["mode"] = history["mode"].str.lower()
    history = history[history["mode"].isin(config.TIME_CONTROLS)]
    history["date"] = pd.to_datetime(history[["year", "month", "day"]])
    history = history.drop_duplicates(subset=["username", "mode", "date"])
    return history[["username", "mode", "date", "rating"]].sort_values("date")


# per-player view of games: each game becomes two rows (white and black)
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
    return pg.groupby("username")["won"].mean().rename("win_rate")

def draw_rate(pg: pd.DataFrame) -> pd.Series:
    return pg.groupby("username")["drew"].mean().rename("draw_rate")

def avg_moves(pg: pd.DataFrame) -> pd.Series:
    return (pg.groupby("username")["turns"].mean() / 2).rename("avg_moves")

def time_control_shares(pg: pd.DataFrame) -> pd.DataFrame:
    # only time controls that appear in the data (an all-zero column adds nothing)
    shares = pd.crosstab(pg["username"], pg["speed"], normalize="index")
    played = [tc for tc in config.TIME_CONTROLS if tc in shares.columns]
    return shares[played].add_prefix("share_")

def profile_attributes(profiles: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    attrs = pd.DataFrame(index=profiles["username"])
    created = pd.to_datetime(profiles["created_at_account"], unit="ms")
    attrs["account_age_days"] = (reference_date - created).dt.days.values
    attrs["title"] = profiles["title"].fillna("none").values
    for tc in ["bullet", "blitz", "rapid"]:
        attrs[f"games_{tc}"] = profiles[f"total_{tc}_games"].values
    return attrs


# main time control = the one with the most games among the sampled (recent) games.
# we use recent games rather than lifetime profile totals, because some players
# switched format (e.g. lots of bullet years ago, only blitz now), and the targets
# measure recent improvement
def main_time_control(pg: pd.DataFrame) -> pd.Series:
    counts = pd.crosstab(pg["username"], pg["speed"])
    return counts.idxmax(axis=1).rename("main_tc")


# current rating = rating in the most recent sampled game in the player's main time control
def current_rating(pg: pd.DataFrame, main_tc: pd.Series) -> pd.Series:
    pg = pg[pg["speed"] == pg["username"].map(main_tc)].sort_values("created_at")
    return pg.groupby("username")["rating"].last().rename("rating")


# number of different opponents divided by number of games:
# close to 1 = plays many different people, close to 0 = plays the same few people
def opponents_per_game(pg: pd.DataFrame) -> pd.Series:
    by_player = pg.groupby("username")
    return (by_player["opponent"].nunique() / by_player.size()).rename("opponents_per_game")


# how varied a player's openings are: entropy over the opening families played.
# 0 = always the same opening, higher = spread over more openings.
# we use the opening family (the part before ":"), e.g. "Sicilian Defense",
# so small variations of the same opening don't count as different openings
def opening_diversity(pg: pd.DataFrame) -> pd.Series:
    family = pg["opening"].str.split(":").str[0].str.strip()
    counts = pd.crosstab(pg["username"], family)
    shares = counts.div(counts.sum(axis=1), axis=0)
    entropy = -(shares * np.log2(shares.where(shares > 0))).sum(axis=1)
    return entropy.rename("opening_diversity")


# targets

# rating growth from the sampled games: rating in the last game minus the first,
# in the player's main time control (short window, usually 2-3 weeks)
def growth_from_games(pg: pd.DataFrame, main_tc: pd.Series) -> pd.Series:
    pg = pg[pg["speed"] == pg["username"].map(main_tc)].sort_values("created_at")
    by_player = pg.groupby("username")["rating"]
    growth = (by_player.last() - by_player.first()).where(by_player.size() >= 2)
    return growth.rename("target_growth_games")


# rating growth over a window of `months` months ending at `reference_date`,
# in the player's main time control, from the full rating history.
# start rating = last point on or before the window start
# end rating   = last point on or before the reference date
# NaN if:
# - the player has too little rating history before the window start
#   (new account, or barely played this time control), so their start rating
#   isn't reliable yet: see config.MIN_HISTORY_DAYS_BEFORE_WINDOW
# - there is no rating change inside the window (inactive)
def growth_from_history(history: pd.DataFrame, main_tc: pd.Series,
                        reference_date: pd.Timestamp, months: int) -> pd.Series:
    start_date = reference_date - pd.DateOffset(months=months)
    h = history[history["mode"] == history["username"].map(main_tc)]
    h = h[h["date"] <= reference_date]

    before = h[h["date"] <= start_date].groupby("username")["rating"]
    inside = h[h["date"] > start_date].groupby("username")["rating"].last()

    enough_history = before.size() >= config.MIN_HISTORY_DAYS_BEFORE_WINDOW
    start_rating = before.last()[enough_history]

    growth = (inside - start_rating).dropna()
    return growth.rename(f"target_growth_{months}m")


# binary version: 1 if in the top 20% by growth, 0 otherwise, NaN if growth is missing
def top20(growth: pd.Series) -> pd.Series:
    threshold = growth.quantile(0.8)
    binary = (growth >= threshold).astype(float).where(growth.notna())
    return binary.rename(f"{growth.name}_top20")


# build and save player table
def build_player_table() -> pd.DataFrame:
    profiles = load_profiles()
    games = load_games()
    history = load_rating_history()
    pg = player_games(games)

    # only keep rows for our core players (games against opponents still count)
    core = set(profiles["username"])
    pg = pg[pg["username"].isin(core)]

    # one fixed date for account age and growth windows, so results don't
    # depend on when the script is run: the date of the most recent game
    reference_date = pd.to_datetime(games["created_at"].max(), unit="ms").normalize()

    players = pd.DataFrame(index=sorted(core))
    players.index.name = "username"
    players = players.join(pg.groupby("username").size().rename("n_games"))
    players = players.join(win_rate(pg))
    players = players.join(draw_rate(pg))
    players = players.join(avg_moves(pg))
    players = players.join(time_control_shares(pg))
    players = players.join(profile_attributes(profiles, reference_date))
    players = players.join(main_time_control(pg))
    players = players.join(current_rating(pg, players["main_tc"]))
    players = players.join(opponents_per_game(pg))
    players = players.join(opening_diversity(pg))

    # 50-game filter: enough rated games in the main time control (profile totals)
    games_main = players.apply(lambda r: r.get(f"games_{r['main_tc']}", 0), axis=1)
    players = players[games_main >= config.MIN_GAMES_MAIN_TC]

    # targets
    players = players.join(growth_from_games(pg, players["main_tc"]))
    for months in config.GROWTH_WINDOWS_MONTHS:
        growth = growth_from_history(history, players["main_tc"], reference_date, months)
        players = players.join(growth)
        players = players.join(top20(players[growth.name]))

    return players.reset_index()


# all players (core + opponents): only profile- and history-based columns,
# since opponents only have ~1 sampled game each

# main time control from the rating history: the time control with the most days
# with rating changes in the last config.MAIN_TC_RECENT_MONTHS months.
# players without recent activity fall back to their lifetime profile totals
def main_time_control_from_history(history: pd.DataFrame, attrs: pd.DataFrame,
                                   reference_date: pd.Timestamp) -> pd.Series:
    start = reference_date - pd.DateOffset(months=config.MAIN_TC_RECENT_MONTHS)
    recent = history[(history["date"] > start) & (history["date"] <= reference_date)]
    recent_tc = pd.crosstab(recent["username"], recent["mode"]).idxmax(axis=1)

    lifetime_tc = (attrs[["games_bullet", "games_blitz", "games_rapid"]]
                   .idxmax(axis=1).str.replace("games_", ""))
    return recent_tc.reindex(attrs.index).fillna(lifetime_tc).rename("main_tc")


# current rating = last rating on or before the reference date, in the main time control
def rating_from_history(history: pd.DataFrame, main_tc: pd.Series,
                        reference_date: pd.Timestamp) -> pd.Series:
    h = history[(history["mode"] == history["username"].map(main_tc))
                & (history["date"] <= reference_date)]
    return h.groupby("username")["rating"].last().rename("rating")


def build_all_players_table(reference_date: pd.Timestamp) -> pd.DataFrame:
    core_profiles = load_profiles()
    opponent_profiles = load_profiles(config.OPPONENT_PROFILES_FILE)
    # some core players also appear in the opponent profiles: keep the core version
    profiles = (pd.concat([core_profiles, opponent_profiles], ignore_index=True)
                .drop_duplicates(subset="username", keep="first"))

    history = load_rating_history(
        [config.RATING_HISTORY_FILE, *config.OPPONENT_RATING_HISTORY_FILES])

    # only players who appear in at least one cleaned game; otherwise they would
    # have no edges in the network (e.g. opponents who only played ultraBullet)
    games = load_games()
    in_games = set(games["white_player"]) | set(games["black_player"])
    profiles = profiles[profiles["username"].isin(in_games)]

    players = profile_attributes(profiles, reference_date)
    players.index.name = "username"
    players.insert(0, "is_core", players.index.isin(core_profiles["username"]))
    players = players.join(main_time_control_from_history(history, players, reference_date))
    players = players.join(rating_from_history(history, players["main_tc"], reference_date))

    # 50-game filter: enough rated games in the main time control (profile totals)
    games_main = players.apply(lambda r: r.get(f"games_{r['main_tc']}", 0), axis=1)
    players = players[games_main >= config.MIN_GAMES_MAIN_TC]

    # targets: same windows and checks as for the core players
    for months in config.GROWTH_WINDOWS_MONTHS:
        growth = growth_from_history(history, players["main_tc"], reference_date, months)
        players = players.join(growth)
        players = players.join(top20(players[growth.name]))

    return players.reset_index()


if __name__ == "__main__":
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    table = build_player_table()
    table.to_csv(config.PLAYERS_TABLE, index=False)
    print(f"Saved {len(table)} players to {config.PLAYERS_TABLE}")

    # same reference date as the core table: the date of the most recent game
    reference_date = pd.to_datetime(load_games()["created_at"].max(), unit="ms").normalize()
    all_table = build_all_players_table(reference_date)
    all_table.to_csv(config.PLAYERS_ALL_TABLE, index=False)
    print(f"Saved {len(all_table)} players ({all_table['is_core'].sum()} core) "
          f"to {config.PLAYERS_ALL_TABLE}")