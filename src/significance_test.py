# Permutation significance test for the best subgroup of the active network dataset.

# Run from the repo root, after src.features and src.edges:  python -m src.significance_test
# The dataset, target, column roles, score, permutation count, significance level
# and plot location all come from src.config (NETWORK_* and SIGNIFICANCE_* entries).
# The score is not recomputed here: set SIGNIFICANCE_SCORE to the best q reported
# by src/network_mining.py. Output:
#   the PNG at config.SIGNIFICANCE_PLOT_FILE (histogram of permuted best scores)

from pathlib import Path

from src import config
from src import network_mining
from algorithm.methods import significance_test


# run the permutation test for the active dataset and return the p-value
def run(score=config.SCORE_TO_TEST,
        n=config.SIGNIFICANCE_N,
        significance_level=config.SIGNIFICANCE_LEVEL,
        output_file=config.SIGNIFICANCE_PLOT_FILE):
    dataset = config.NETWORK_DATASETS[config.NETWORK_DATASET]

    if score is None:
        raise ValueError("Set SIGNIFICANCE_SCORE in src/config.py")

    graph, players = network_mining.load_network()
    lu = network_mining.build_lookup(players)

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    return significance_test(
        graph,
        lu,
        dataset["target"],
        score,
        dataset["columns_to_ignore"],
        dataset["categorical_columns"],
        n=n,
        significance_level=significance_level,
        output_file=output_file,
    )


if __name__ == "__main__":
    p_value = run()

    verdict = "SIGNIFICANT" if p_value <= config.SIGNIFICANCE_LEVEL else "NOT SIGNIFICANT"
    print(f"score = {config.SCORE_TO_TEST}  p-value = {p_value:.4f} "
          f"({verdict} at {config.SIGNIFICANCE_LEVEL})")
    print(f"Saved plot to {config.SIGNIFICANCE_PLOT_FILE}")
