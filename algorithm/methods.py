import copy
import pandas as pd
import numpy as np
import tqdm
import networkx as nx
import gower
import matplotlib.pyplot as plt

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, List, Tuple

from src.quality_measures import ks_quality


def top_k_func(groups: pd.DataFrame, k: int) -> pd.DataFrame:
    """
    Selects the top k rows from the dataset while removing rows
    that have high overlap in 'reference' and 'subgroup' columns.

    Args:
        groups (pd.DataFrame): The DataFrame containing group information.
        k (int): The number of rows to keep after filtering.

    Returns:
        pd.DataFrame: The filtered top k rows.
    """
    top_k = copy.deepcopy(groups)
    i = 0
    while i < len(top_k) and i < k:
        top_group = top_k.iloc[i]
        ref_group = set(top_group['reference'])
        sub_group = set(top_group['subgroup'])

        rows_to_drop = []
        for idx, row in top_k.iloc[i + 1:].iterrows():
            overlap_ref = len(ref_group.intersection(row['reference'])) / (len(ref_group) if len(ref_group) else 1)
            overlap_sub = len(sub_group.intersection(row['subgroup'])) / (len(sub_group) if len(sub_group) else 1)
            if overlap_ref > 0.75 and overlap_sub > 0.75:
                rows_to_drop.append(idx)

        top_k = top_k.drop(rows_to_drop)
        i += 1

    return top_k.iloc[:k]


def get_attributes(
    x: int,
    lu: pd.DataFrame,
    drop_cols: List[str] = None
) -> pd.Series:
    if drop_cols is None:
        drop_cols = ["target"]

    attribute_cols = lu.columns.drop(
        [col for col in drop_cols if col in lu.columns]
    )

    return lu.loc[x, attribute_cols]


def ranking(x: int, s: nx.Graph, lu: pd.DataFrame, target_name: str ='target', columns_to_ignore: List[str] = [], categorical_cols: List[str] = []) -> List[Tuple[Any, Any]]:
    """
    Computes a ranking of other nodes based on shortest path lengths
    and breaks ties using gower distances.

    Args:
        x (int): The reference node.
        s (nx.Graph): The network graph.
        lu (pd.DataFrame): The lookup DataFrame with attributes.
        columns_to_ignore (list): Columns to ignore when calculating the gower distance
        categorical_cols (list): a list with the name of the categorical columns


    Returns:
        List[Tuple[Any, Any]]: A list of tuples (node, target) in ranked order.
    """
    attribute_cols = [
        col for col in lu.columns
        if col not in columns_to_ignore
    ]

    categorical_cols = [
        col for col in categorical_cols
        if col in attribute_cols
    ]

    cat_features = [
        col in categorical_cols for col in attribute_cols
    ]


    d_dict = nx.shortest_path_length(s, x, weight="weight")
    distances = list(d_dict.values())
    D = list(zip(d_dict.keys(), d_dict.values()))

    for d in np.unique(distances):
        left = distances.index(d)
        right = len(distances) - distances[::-1].index(d)
        tie_list = D[left:right]

        reference = lu.loc[[x], attribute_cols]
        candidates = lu.loc[
            [node for node, _ in tie_list],
            attribute_cols
        ]

        gower_distances = gower.gower_matrix(
            reference,
            candidates,
            cat_features=cat_features
        )[0]

        sorted_gower = [
            node_distance
            for _, node_distance in sorted(
                zip(gower_distances, tie_list),
                key=lambda item: item[0]
            )
        ]
        D[left:right] = sorted_gower

    # nodes without a target are skipped: the graph stays intact, so shortest
    # paths still go through them, but they never count towards the score.
    ranks = [
        (node, lu.loc[node, target_name])
        for node, _ in D
        if pd.notna(lu.loc[node, target_name])
    ]
    return ranks


def q_func(s: List[Tuple[Any, int]], g: List[Tuple[Any, int]], target: str) -> float:
    """
    Computes the WRAcc-based quality measure Q for a given subgroup.

    Args:
        s (List[Tuple[Any, int]]): The subgroup's (node, target) pairs.
        g (List[Tuple[Any, int]]): The whole population's (node, target) pairs.
        target (str): Not used in this function, included for consistency.

    Returns:
        float: The quality measure Q.
    """
    s_size = len(s)
    g_size = len(g)
    if s_size == 0 or g_size == 0:
        return 0

    cover = s_size / g_size
    n_target_s = sum([x[1] for x in s])
    n_target_g = sum([x[1] for x in g])

    wr_acc = (cover ** 0.5) * ((n_target_s / s_size) - (n_target_g / g_size))
    return abs(wr_acc)


def discovery(ranks: List[Tuple[Any, Any]],
              g: nx.Graph,
              lu: pd.DataFrame,
              target_name: str,
              ablation_mode: bool = False
              ) -> Tuple[int, int, float, List[Tuple[Any, Any]]]:
    """
    Determines thresholds rho and sigma based on the Q measure.

    Args:
        ranks (List[Tuple[Any, Any]]): Ranked list of (node, target).
        g (nx.Graph): The whole graph.
        lu (pd.DataFrame): Lookup DataFrame.
        ablation_mode (bool): If True, adjusts the search for sigma.

    Returns:
        Tuple[int, int, float, List[Tuple[Any, Any]]]:
            (rho, sigma, best_quality, ranks)
    """
    # g_list_target = list(zip(list(g.nodes), [lu.loc[x][target_name] for x in list(g.nodes)]))
    population_values = lu.loc[
        list(g.nodes), target_name
    ].dropna().to_numpy()

    if not ablation_mode:
        rho = 0
        sigma = 0
        best = 0

        temp_ranks = [x for x in ranks[0:4]]
        for i in range(5, len(ranks) + 1):
            temp_ranks.append(ranks[i - 1])
            # q = q_func(temp_ranks, g_list_target, target_name)
            q = ks_quality([x[1] for x in temp_ranks], population_values)
            if q >= best:
                best = q
                rho = i

        best = 0
        temp_ranks = [x for x in ranks[0:2]]
        for i in range(3, rho + 1):
            temp_ranks.append(ranks[i - 1])
            # q = q_func(temp_ranks, [x for x in ranks[0:rho]], target_name)
            q = ks_quality([x[1] for x in temp_ranks], [x[1] for x in ranks[0:rho]])
            if q >= best:
                best = q
                sigma = i

        return rho, sigma, best, ranks

    else:
        rho = len(ranks)
        best = 0
        sigma = 0
        temp_ranks = [x for x in ranks[0:4]]
        for i in range(5, rho + 1):
            temp_ranks.append(ranks[i - 1])
            # q = q_func(temp_ranks, g_list_target, target_name)
            q = ks_quality([x[1] for x in temp_ranks], population_values)
            if q >= best:
                best = q
                sigma = i
        return rho, sigma, best, ranks


def process_node(node: int,
                 g: nx.Graph,
                 lu: pd.DataFrame,
                 target_name: str,
                 columns_to_ignore: List[str],
                 categorical_attributes: List[str],
                 ablation_mode: bool = False
                 ) -> Tuple[int, int, int, float, List[Tuple[Any, Any]]]:
    """
    Processes a single node by computing its ranking and subgroup qualities.

    Args:
        node (int): The node to process.
        g (nx.Graph): The whole graph.
        lu (pd.DataFrame): Lookup DataFrame with attributes.
        ablation_mode (bool): If True, adjusts discovery logic.

    Returns:
        Tuple[int, int, int, float, List[Tuple[Any, Any]]]:
            (node, rho, sigma, q, ranks)
    """
    ranks = ranking(node, g, lu, target_name, columns_to_ignore, categorical_attributes)
    rho, sigma, q, ranks = discovery(ranks, g, lu, target_name, ablation_mode=ablation_mode)
    return node, rho, sigma, q, ranks


def find_groups(g: nx.Graph,
                k: int,
                lu: pd.DataFrame,
                target_name: str,
                columns_to_ignore: List[str],
                categorical_attributes: List[str],
                ablation_mode: bool = False,
                use_multiprocessing: bool = True,
                show_progress: bool = True
                ) -> pd.DataFrame:
    """
    Finds subgroups in the graph, either in parallel (multiprocessing) or
    single-threaded, based on the 'use_multiprocessing' parameter.

    Args:
        g (nx.Graph): The whole graph to analyze.
        k (int): Number of top groups to return.
        lu (pd.DataFrame): Lookup DataFrame with attributes.
        ablation_mode (bool): If True, uses ablation variant of discovery.
        use_multiprocessing (bool): Whether to enable multiprocessing.

    Returns:
        pd.DataFrame: Filtered top k rows with references and subgroups.
    """
    out_rows = []

    if use_multiprocessing:
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(process_node, node, g, lu, target_name, columns_to_ignore, categorical_attributes, ablation_mode): node
                for node in g.nodes
            }

            for future in tqdm.tqdm(as_completed(futures), total=len(g.nodes), disable=not show_progress):
                node_result = future.result()
                out_rows.append(node_result)
    else:
        for node in tqdm.tqdm(g.nodes, disable=not show_progress):
            node_result = process_node(node, g, lu, target_name, columns_to_ignore, categorical_attributes, ablation_mode)
            out_rows.append(node_result)

    out = pd.DataFrame(out_rows, columns=['node', 'rho', 'sigma', 'q', 'ranks']).set_index('node')

    out = out.sort_values(by=['q'], ascending=False)

    out['reference'] = [[] for _ in range(len(out))]
    out['subgroup'] = [[] for _ in range(len(out))]

    for index, row in out.iterrows():
        out.at[index, 'reference'] = [x[0] for x in row['ranks'][0:row['rho']]]
        out.at[index, 'subgroup'] = [x[0] for x in row['ranks'][0:row['sigma']]]

    return top_k_func(out, k)

def get_permutation_scores(
        g: nx.Graph,
        lu: pd.DataFrame,
        target_name: str,
        columns_to_ignore: List[str] = [],
        categorical_attributes: List[str] = [],
        n:int = 500):
    """
        Runs the find_groups function for n times shuffling the target everytime
    Args:
        g (nx.Graph): The whole graph to analyze.
        lu (pd.DataFrame): Lookup DataFrame with attributes.
        target_name (str): The name of the target column.
        n (int): Number of iterations to run.
    Returns:
        a list with the best scores of each iteration
    """

    scores = []
    lu_copy = lu.copy()
    seed = np.random.default_rng(seed=37)

    for _ in tqdm.tqdm(range(n)):
        lu_copy[target_name] = seed.permutation(lu_copy[target_name].values)

        best_score = find_groups(
            g,
            1,
            lu_copy,
            target_name,
            columns_to_ignore,
            categorical_attributes,
            show_progress = False)['q'].iloc[0]

        scores.append(best_score)

    return scores

def significance_test(g: nx.Graph,
                      lu: pd.DataFrame,
                      target_name: str,
                      score_to_test: float,
                      columns_to_ignore: List[str] = [],
                      categorical_attributes: List[str] = [],
                      n:int = 500,
                      significance_level = 0.05,
                      output_file = None):

    """
        Runs the get_permutation_scores function and plots the results
    Args:
        g (nx.Graph): The whole graph to analyze.
        lu (pd.DataFrame): Lookup DataFrame with attributes.
        target_name (str): The name of the target column.
        score_to_test (float): The score to test if its statistically significant
        n (int): Number of iterations to run.
        output_file: If given, the histogram is saved there instead of shown.
    Returns:
        a list with the best scores of each iteration
    """

    scores = np.array(get_permutation_scores(g, lu, target_name, columns_to_ignore, categorical_attributes, n))

    p_value = (1 + np.sum(scores >= score_to_test)) / (len(scores) + 1)
    threshold = np.quantile(scores, 1 - significance_level)

    plt.hist(scores, bins=30, edgecolor="black", alpha=0.7)

    plt.axvline(
        score_to_test,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Original score = {score_to_test:.3f}"
    )

    plt.axvline(
        threshold,
        color="orange",
        linestyle=":",
        linewidth=1,
        label=f"{int((1 - significance_level) * 100)}th percentile = {threshold:.3f}"
    )

    result = "SIGNIFICANT" if p_value <= significance_level else "NOT SIGNIFICANT"

    plt.title(f"Permutation test: {result} (p = {p_value:.4f})")
    plt.xlabel("Best quality under permutation")
    plt.ylabel("Frequency")
    plt.legend(loc="upper left")
    plt.tight_layout()
    if output_file is not None:
        plt.savefig(output_file, dpi=200, bbox_inches="tight")
        plt.close()
    else:
        plt.show()

    return p_value
