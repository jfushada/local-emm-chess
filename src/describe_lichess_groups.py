# Describe the best Lichess subgroup per quality measure (for Section 6.2).

# Run from the repo root:  python -m src.describe_lichess_groups
# Reads the mining results (results/mined_groups/..._min_rho_40.csv) and the player
# table, and prints for the best subgroup (first row) of each measure: its size,
# the target values and ratings of its players, and the reference group's target.

import ast

import pandas as pd

from src import config

RUNS = [
    ("mean", "target_growth_3m"),
    ("ks", "target_growth_3m"),
    ("wracc", "target_growth_3m_top20"),
]

players = pd.read_csv(config.PLAYERS_SNOWBALL_TABLE).set_index("username")
growth = players["target_growth_3m"]

for measure, target in RUNS:
    path = (config.MINED_GROUPS_DIR /
            f"network_groups_snowball_{target}_{measure}_min_rho_{config.NETWORK_MIN_RHO}.csv")
    best = pd.read_csv(path).iloc[0]
    sigma = ast.literal_eval(best["subgroup"])
    rho = ast.literal_eval(best["reference"])
    print(f"\n=== {measure} ({target}) ===")
    print(f"|S_sigma| = {len(sigma)}, |R_rho| = {len(rho)}")
    print("subgroup growth:", sorted(round(g) for g in growth[sigma].dropna()))
    print("subgroup ratings:", sorted(int(r) for r in players.loc[sigma, "rating"]),
          "| median", players.loc[sigma, "rating"].median())
    print("subgroup main_tc:", players.loc[sigma, "main_tc"].value_counts().to_dict())
    if measure == "wracc":
        print("subgroup in top 20%:", int(players.loc[sigma, target].sum()), "of", len(sigma),
              "| reference share: %.2f" % players.loc[rho, target].mean())
    print("reference growth: mean %.1f, median %.1f (n = %d)"
          % (growth[rho].mean(), growth[rho].median(), growth[rho].notna().sum()))