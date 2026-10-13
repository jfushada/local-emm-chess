# Local subgroup discovery on the player network.

# Same procedure as "Lichess discovery.ipynb", but wired through the shared
# helpers in src: the dataset comes from src.config, the graph is built by
# src.plot_network.load_graph and the mining itself is algorithm.methods.find_groups.

# Run from the repo root, after src.features and src.edges:  python -m src.network_mining
# Output:
#   results/network_groups_<dataset>_<target>.csv   the top subgroups, one row per player (node)

from src import config
from src.plot_network import load_graph
from algorithm.methods import find_groups

# Which tables, target and column roles to use is chosen in src/config.py via
# NETWORK_DATASET; everything below is read from that entry.
DATASET = config.NETWORK_DATASETS[config.NETWORK_DATASET]

# title and time control are the only categorical attributes; gower needs to
# know, otherwise it treats the category indices as numbers.
CATEGORICAL_COLUMNS = DATASET["categorical_columns"]

# columns that identify the row or that encode the target (or another target).
# They must not be used as attributes (see the "Columns to exclude per target"
# table in README).
COLUMNS_TO_IGNORE = DATASET["columns_to_ignore"]


# node table + edge list -> graph and lookup table (same inputs as the notebook)
def load_network(players_file=DATASET["players"], edges_file=DATASET["edges"]):
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
# the target and k come from src/config.py. players with a missing target stay
# in the graph (topology) but are skipped when the score is computed (see ranking).
def run(target_name=DATASET["target"], k=config.NETWORK_TOP_GROUPS):
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

    out_file = (config.ROOT / "results"
                / f"network_groups_{config.NETWORK_DATASET}_{DATASET['target']}.csv")
    out_file.parent.mkdir(exist_ok=True)
    result.to_csv(out_file)
    print(f"Saved {len(result)} subgroups to {out_file}")
