# Build the edge lists of the player network: one row per pair of players
# who played each other in the sampled games.

# Run from the repo root, after src.features:  python -m src.edges
# Output:
#   data/processed/edges_all.csv   edges between players in players_all.csv
#   data/processed/edges_core.csv  edges between core players only (players.csv)
#
# Columns: player_a, player_b, n_games, distance
#   - player_a < player_b (alphabetical), so each pair appears once
#   - distance = 1 / n_games, so frequent opponents are close.
#     When building a networkx graph for the LSD code, use `distance` as the
#     edge "weight" (shortest paths treat "weight" as the length of an edge).
#
# Note: we only downloaded the games of the core players, so every edge contains
# at least one core player. There are no opponent-opponent edges.

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


if __name__ == "__main__":
    games = load_games()   # same cleaning as for the player tables

    for nodes_file, edges_file in [(config.PLAYERS_ALL_TABLE, config.EDGES_ALL_TABLE),
                                   (config.PLAYERS_TABLE, config.EDGES_CORE_TABLE)]:
        nodes = set(pd.read_csv(nodes_file)["username"])
        edges = build_edges(games, nodes)
        edges.to_csv(edges_file, index=False)
        print(f"Saved {len(edges)} edges between {len(nodes)} players to {edges_file}")