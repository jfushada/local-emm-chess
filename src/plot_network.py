# Plot the player network from the edge lists.

# Run from the repo root, after src.edges:  python -m src.plot_network
# Output (in results/):
#   network_core.png           players.csv + edges_core.csv
#   network_all.png            players_all.csv + edges_all.csv
#   network_snowball_core.png  players_snowball.csv + edges_snowball_core.csv  (if built)
#   network_snowball.png       players_all.csv + edges_snowball.csv           (if built)
#
# Core players are blue, other players (opponents / snowball players) orange.
# Node size grows with the number of connections, and thicker lines mean more
# games between two players. The 5,100-player plots take about a minute each.

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D

from src import config

CORE_COLOR = "#2a78d6"       # blue
OPPONENT_COLOR = "#eb6834"   # orange
EDGE_COLOR = "#52514e"
TEXT_COLOR = "#0b0b0b"
BACKGROUND = "#fcfcfb"


# build a networkx graph; `distance` goes into "weight" so shortest paths use it as the length
def load_graph(players_file, edges_file) -> tuple[nx.Graph, pd.DataFrame]:
    players = pd.read_csv(players_file).set_index("username")
    edges = pd.read_csv(edges_file)

    graph = nx.Graph()
    graph.add_nodes_from(players.index)
    for row in edges.itertuples():
        graph.add_edge(row.player_a, row.player_b, weight=row.distance, n_games=row.n_games)
    return graph, players


def plot_network(graph: nx.Graph, players: pd.DataFrame, title: str, out_file,
                 label_top: int = 0, other_label: str = "opponent") -> None:
    if "is_core" in players:
        is_core = players["is_core"]
    elif "is_snowball" in players:
        is_core = ~players["is_snowball"]
    else:
        is_core = pd.Series(True, players.index)

    # layout: unweighted, so the picture shows who is connected rather than how often
    pos = nx.spring_layout(graph, seed=42, k=1.5 / len(graph) ** 0.5, iterations=50)

    degree = dict(graph.degree())
    sizes = [8 + 4 * degree[n] ** 0.8 for n in graph.nodes]
    colors = [CORE_COLOR if is_core.get(n, False) else OPPONENT_COLOR for n in graph.nodes]
    widths = [0.3 + 0.4 * graph.edges[e]["n_games"] ** 0.5 for e in graph.edges]

    fig, ax = plt.subplots(figsize=(10, 10), facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    nx.draw_networkx_edges(graph, pos, ax=ax, width=widths, edge_color=EDGE_COLOR, alpha=0.35)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=sizes, node_color=colors,
                           edgecolors=BACKGROUND, linewidths=0.5)

    # label the best-connected players, so the hubs can be identified
    if label_top:
        top = sorted(degree, key=degree.get, reverse=True)[:label_top]
        nx.draw_networkx_labels(graph, pos, labels={n: n for n in top}, ax=ax,
                                font_size=7, font_color=TEXT_COLOR)

    legend = [Line2D([], [], marker="o", linestyle="", color=CORE_COLOR, label="core player")]
    if not is_core.all():
        legend.append(Line2D([], [], marker="o", linestyle="", color=OPPONENT_COLOR, label=other_label))
    if len(legend) > 1:
        ax.legend(handles=legend, loc="upper right", frameon=False, labelcolor=TEXT_COLOR)

    ax.set_title(title, color=TEXT_COLOR, loc="left")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_file, dpi=200, facecolor=BACKGROUND)
    plt.close(fig)
    print(f"Saved {out_file}")


if __name__ == "__main__":
    results = config.ROOT / "results"
    results.mkdir(exist_ok=True)

    graph, players = load_graph(config.PLAYERS_TABLE, config.EDGES_CORE_TABLE)
    plot_network(graph, players,
                 f"Core players: {graph.number_of_nodes()} players, {graph.number_of_edges()} edges",
                 results / "network_core.png", label_top=5)

    graph, players = load_graph(config.PLAYERS_ALL_TABLE, config.EDGES_ALL_TABLE)
    plot_network(graph, players,
                 f"All players: {graph.number_of_nodes()} players, {graph.number_of_edges()} edges",
                 results / "network_all.png")

    if config.EDGES_SNOWBALL_CORE_TABLE.exists():
        graph, players = load_graph(config.PLAYERS_SNOWBALL_TABLE, config.EDGES_SNOWBALL_CORE_TABLE)
        plot_network(graph, players,
                     f"Core + snowball players: {graph.number_of_nodes()} players, "
                     f"{graph.number_of_edges()} edges",
                     results / "network_snowball_core.png", other_label="snowball player")

    if config.EDGES_SNOWBALL_TABLE.exists():
        graph, players = load_graph(config.PLAYERS_ALL_TABLE, config.EDGES_SNOWBALL_TABLE)
        plot_network(graph, players,
                     f"All players, with snowball games: {graph.number_of_nodes()} players, "
                     f"{graph.number_of_edges()} edges",
                     results / "network_snowball.png")