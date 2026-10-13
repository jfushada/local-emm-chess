# Local subgroup discovery on the player network.

# Same procedure as "Lichess discovery.ipynb", but wired through the shared
# helpers in src: the paths come from src.config, the graph is built by
# src.plot_network.load_graph and the mining itself is algorithm.methods.find_groups.

# Run from the repo root, after src.features and src.edges:  python -m src.network_mining
# Output:
#   results/network_groups_<target>.csv   the top subgroups, one row per player (node)

from src import config
from src.plot_network import load_graph
from algorithm.methods import find_groups

# title and time control are the only categorical attributes; gower needs to
# know, otherwise it treats the category indices as numbers.
CATEGORICAL_COLUMNS = ["title", "main_tc"]

# username identifies the row, rating is the end point of the rating-growth
# targets and the other target_* columns are different targets. None of them may
# be used as attributes (see the "Columns to exclude per target" table in README).
COLUMNS_TO_IGNORE = [
    "username",
    "rating",
    "target_growth_games",
    "target_growth_1m", "target_growth_1m_top20",
    "target_growth_3m", "target_growth_3m_top20",
    "target_growth_6m", "target_growth_6m_top20",
]


# node table + edge list -> graph and lookup table (same inputs as the notebook)
def load_network(players_file=config.PLAYERS_SNOWBALL_TABLE,
                 edges_file=config.EDGES_SNOWBALL_CORE_TABLE):
    return load_graph(players_file, edges_file)


# every attribute that is not categorical becomes a float, so gower can rank the
# neighbours that are tied on shortest path by their distance. The ignored
# columns keep their dtype.
def build_lookup(players):
    lu = players.copy()
    for col in lu.columns:
        if col not in CATEGORICAL_COLUMNS + COLUMNS_TO_IGNORE:
            lu[col] = lu[col].astype(float)
    return lu


# run the local subgroup discovery and return the top k subgroups.
# the target and k are set in src/config.py. players with a missing target stay
# in the graph (topology) but are skipped when the score is computed (see ranking).
def run(target_name=config.NETWORK_TARGET,
        k=config.NETWORK_TOP_GROUPS):
    graph, players = load_network()
    lu = build_lookup(players)

    return find_groups(
        graph,
        k,
        lu,
        target_name,
        COLUMNS_TO_IGNORE,
        CATEGORICAL_COLUMNS,
    )


if __name__ == "__main__":
    result = run()

    out_file = config.ROOT / "results" / f"network_groups_{config.NETWORK_TARGET}.csv"
    out_file.parent.mkdir(exist_ok=True)
    result.to_csv(out_file)
    print(f"Saved {len(result)} subgroups to {out_file}")
