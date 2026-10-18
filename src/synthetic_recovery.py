# How well does the search recover the planted subgroups in the synthetic networks?

# Run from the repo root, after generating the networks
# (cd fake_node_generator && python main.py):
#     python -m src.synthetic_recovery
# Output: results/synthetic_recovery.csv, one row per network x quality measure x planted group
#
# For every prototype the search returns a reference group (rho) and a subgroup
# (sigma). For each planted group we take the best Jaccard overlap with any sigma
# (and any rho) among the top results. sigma is what should match the planted
# group; rho is reported to check it isn't just the planted group itself.
# The minimum rho size comes from config.NETWORK_MIN_RHO (5 = original method).

import networkx as nx
import pandas as pd

from src import config, quality_measures
from algorithm.methods import find_groups

# quality measure -> target it is run on. mean and KS use the numerical target;
# wracc is the binary baseline (the original method), on the top-20% version
# of the same target that the generator writes as WKL_target_bin
MEASURES = {
    "mean": "target",
    "ks": "target",
    "wracc": "WKL_target_bin",
}
TOP = 20  # results to look at (after removing overlaps)
CATEGORICAL = ["title", "main_tc"]
# rating is no leakage here (the synthetic target doesn't depend on it), and the
# generator uses it to break ties when planting, so it is kept as an attribute.
# both targets are ignored as attributes, whichever one is being mined
IGNORE = ["id", "target", "group", "WKL_target_bin"]


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b)


def load(network_dir):
    players = pd.read_csv(network_dir / "players.csv").set_index("username")
    players["rating"] = players["rating"].astype(float)
    edges = pd.read_csv(network_dir / "edges.csv")
    graph = nx.Graph()
    graph.add_nodes_from(players.index)
    for row in edges.itertuples():
        graph.add_edge(row.player_a, row.player_b, weight=row.distance)
    planted = pd.read_csv(network_dir / "planted_subgroups.csv").groupby("group")["username"].apply(list)
    return graph, players, planted


# the top results as (q, sigma members, rho members), the same way network_mining
# gets them: find_groups drops results that overlap > 75% with a better one, so
# the top results aren't all copies of the same planted group
def search(graph, players, measure, target, k):
    qm = quality_measures.get_quality_measure(measure)
    found = find_groups(graph, k, players, target, IGNORE, CATEGORICAL,
                        use_multiprocessing=False, show_progress=False, quality_measure=qm,
                        min_rho=config.NETWORK_MIN_RHO)
    return [(row.q, row.subgroup, row.reference) for row in found.itertuples()]


def main():
    networks = pd.read_csv(config.GENERATED_RANGE_DIR / "networks.csv")
    rows = []
    for net in networks.itertuples():
        graph, players, planted = load(config.GENERATED_RANGE_DIR / net.network)
        for measure, target in MEASURES.items():
            top = search(graph, players, measure, target, TOP)
            for group, members in planted.items():
                rows.append({
                    "network": net.network,
                    "shift_sd": net.shift_strength_sd,
                    "size": net.subgroup_size,
                    "seed": net.seed,
                    "measure": measure,
                    "group": group,
                    "sigma_jaccard": max(jaccard(s, members) for _, s, _ in top),
                    "rho_jaccard": max(jaccard(r, members) for _, _, r in top),
                })
            print(f"done {net.network} {measure}")

    out = pd.DataFrame(rows)
    out_file = config.RESULTS_DIR / f"synthetic_recovery_min_rho_{config.NETWORK_MIN_RHO}.csv"
    out.to_csv(out_file, index=False)
    out["found"] = out["sigma_jaccard"] >= 0.9  # (almost) exactly recovered as sigma

    # one row per setting: averaged over the seeds and the planted groups
    summary = (out.groupby(["shift_sd", "size", "measure"])
               .agg(sigma_jaccard=("sigma_jaccard", "mean"),
                    sigma_jaccard_sd=("sigma_jaccard", "std"),
                    rho_jaccard=("rho_jaccard", "mean"),
                    found=("found", "mean"))
               .round(2))
    summary_file = config.RESULTS_DIR / f"synthetic_recovery_summary_min_rho_{config.NETWORK_MIN_RHO}.csv"
    summary.to_csv(summary_file)
    print(summary.to_string())

    # the same per planted group (to see which communities get found)
    print(out.groupby(["group", "measure"])[["sigma_jaccard", "found"]].mean().round(2).to_string())
    print(f"Saved {out_file} and {summary_file}")


if __name__ == "__main__":
    main()