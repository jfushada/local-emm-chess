# Diagnostic: what does the search do when it starts at a planted centre?
# Uses NETWORK_MIN_RHO from src/config.py (5 = the original method).

# Run from the repo root:  python -m src.check_planted_centre shift_3_size_10_seed_0
# For each planted group it prints:
#   1. how many of the first <size> players in the search's ranking are planted
#      (if not all: the search ranks neighbours differently than the generator)
#   2. rho, sigma and q for the centre as prototype
#      (ranking right but sigma != size: the choice of sigma is the problem)
#   3. where that q ranks among all prototypes
#      (sigma right but q ranked low: the scoring / top-k is the problem)

import sys

import pandas as pd

from src import config, quality_measures
from src.synthetic_recovery import CATEGORICAL, IGNORE, load
from algorithm.methods import process_node

network = sys.argv[1] if len(sys.argv) > 1 else "shift_3_size_10_seed_0"
graph, players, planted = load(config.GENERATED_RANGE_DIR / network)
centres = (pd.read_csv(config.GENERATED_RANGE_DIR / network / "planted_subgroups.csv")
           .groupby("group")["centre"].first())
names = pd.read_csv(config.GENERATED_RANGE_DIR / network / "players.csv").set_index("id")["username"]

for measure in ["mean", "ks"]:
    qm = quality_measures.get_quality_measure(measure)
    all_q = {}
    for node in graph.nodes:
        _, rho, sigma, q, ranks = process_node(node, graph, players, "target", IGNORE, CATEGORICAL,
                                               quality_measure=qm, min_rho=config.NETWORK_MIN_RHO)
        all_q[node] = (rho, sigma, q, ranks)
    order = sorted(all_q, key=lambda n: -all_q[n][2])

    print(f"\n=== {network}, {measure} ===")
    for group, members in planted.items():
        centre = names[centres[group]]
        rho, sigma, q, ranks = all_q[centre]
        size = len(members)
        first = [n for n, _ in ranks[:size]]
        print(f"group {group} (centre {centre}, {size} planted)")
        print(f"  1. planted among first {size} ranked: {len(set(first) & set(members))}/{size}")
        print(f"  2. rho={rho}, sigma={sigma}, q={q:.3f}; "
              f"planted in sigma: {len(set(n for n, _ in ranks[:sigma]) & set(members))}/{sigma}, "
              f"in rho: {len(set(n for n, _ in ranks[:rho]) & set(members))}/{rho}")
        print(f"  3. q rank among all {len(order)} prototypes: {order.index(centre) + 1}")
    best = all_q[order[0]]
    print(f"best overall: {order[0]}, rho={best[0]}, sigma={best[1]}, q={best[2]:.3f}")