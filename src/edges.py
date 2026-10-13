# Build the edge lists of the player network: one row per pair of players
# who played each other in the sampled games.

# Run from the repo root, after src.features:  python -m src.edges
# Output:
#   data/processed/edges_all.csv   edges between players in players_all.csv
#   data/processed/edges_core.csv  edges between core players only (players.csv)
#   if the snowball games file exists, also (original + snowball games):
#   data/processed/edges_snowball.csv       edges between players in players_all.csv
#   data/processed/edges_snowball_core.csv  edges between players in players_snowball.csv
#
# Columns: player_a, player_b, n_games, distance
#   - player_a < player_b (alphabetical), so each pair appears once
#   - distance = 1 / n_games, so frequent opponents are close.
#     When building a networkx graph for the LSD code, use `distance` as the
#     edge "weight" (shortest paths treat "weight" as the length of an edge).
#
# Note: in the original crawl we only downloaded the games of the core players, so
# every edge in edges_all/edges_core contains a core player (no opponent-opponent
# edges). The snowball games add edges between opponents.

import pandas as pd
from src import config
from src.features import load_games


# one row per pair of players, with the number of games between them.
# only pairs where both players are in `nodes` are kept
def build_edges(games: pd.DataFrame, nodes: set) -> pd.DataFrame:
    # put each pair in alphabetical order, so alice-bob and bob-alice are the same pair
    pairs = games[["white_player", "black_player"]]
    edges = pd.DataFrame({"player_a": pairs.min(axis=1), "player_b": pairs.max(axis=1)})

    edges = edges.groupby(["player_a", "player_b"]).size().rename("n_games").reset_index()
    edges = edges[edges["player_a"].isin(nodes) & edges["player_b"].isin(nodes)]
    edges["distance"] = 1 / edges["n_games"]
    return edges.reset_index(drop=True)


def save_edges(games: pd.DataFrame, nodes_file, edges_file) -> None:
    nodes = set(pd.read_csv(nodes_file)["username"])
    edges = build_edges(games, nodes)
    edges.to_csv(edges_file, index=False)
    print(f"Saved {len(edges)} edges between {len(nodes)} players to {edges_file}")


if __name__ == "__main__":
    games = load_games()   # same cleaning as for the player tables
    save_edges(games, config.PLAYERS_ALL_TABLE, config.EDGES_ALL_TABLE)
    save_edges(games, config.PLAYERS_TABLE, config.EDGES_CORE_TABLE)

    if config.SNOWBALL_GAMES_FILE.exists():
        # games appearing in both files (snowball player vs core player) count once
        games = (pd.concat([games, load_games(config.SNOWBALL_GAMES_FILE)])
                 .drop_duplicates(subset="game_id"))
        save_edges(games, config.PLAYERS_ALL_TABLE, config.EDGES_SNOWBALL_TABLE)
        save_edges(games, config.PLAYERS_SNOWBALL_TABLE, config.EDGES_SNOWBALL_CORE_TABLE)