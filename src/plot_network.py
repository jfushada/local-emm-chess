# Plot the player network from the edge lists.

# Run from the repo root, after src.edges:  python -m src.plot_network
# Output (in results/):
#   network_core.pdf           players.csv + edges_core.csv
#   network_all.pdf            players_all.csv + edges_all.csv
#   network_snowball_core.pdf  players_snowball.csv + edges_snowball_core.csv  (if built)
#   network_snowball.pdf       players_all.csv + edges_snowball.csv           (if built)
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


# layout: unweighted, so the picture shows who is connected rather than how often.
# each connected component gets its own layout and its own place, side by side
# (largest first, area proportional to its size); laying out everything at once
# can push a few nodes next to the wrong component, which suggests edges
# between components that don't exist
# arrangement: "row" puts the components side by side (wide figure);
# "diagonal" puts each next component down and to the right of the previous one,
# overlapping their boxes but not the networks themselves (roughly square figure)
def layout_by_component(graph: nx.Graph, arrangement: str = "row") -> dict:
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    pos, x_offset, y_offset = {}, 0.0, 0.0
    for component in components:
        sub = graph.subgraph(component)
        width = len(component) ** 0.5
        if len(component) == 1:
            sub_pos = {next(iter(component)): (0.0, 0.0)}
        else:
            sub_pos = nx.spring_layout(sub, seed=42, k=1.5 / len(sub) ** 0.5, iterations=50)
        for node, (x, y) in sub_pos.items():
            # spring_layout returns coordinates in [-1, 1]; scale to the component's width
            pos[node] = (x_offset + (x + 1) / 2 * width, y_offset + (y + 1) / 2 * width)
        if arrangement == "diagonal":
            x_offset += width * 0.62
            y_offset -= width * 0.62
        else:
            x_offset += width * 1.15
    return pos


# width: figure width in inches. 10 for viewing on screen; ~3.4 for one column
# of the ACM two-column layout, so the plot is drawn at the size it is printed
# (node sizes, line widths and fonts are scaled down to match).
def plot_network(graph: nx.Graph, players: pd.DataFrame, title: str, out_file,
                 label_top: int = 0, other_label: str = "opponent",
                 width: float = 10, arrangement: str = "row") -> None:
    if "is_core" in players:
        is_core = players["is_core"]
    elif "is_snowball" in players:
        is_core = ~players["is_snowball"]
    else:
        is_core = pd.Series(True, players.index)

    pos = layout_by_component(graph, arrangement)

    degree = dict(graph.degree())
    scale = width / 10
    sizes = [(8 + 4 * degree[n] ** 0.8) * scale ** 1.5 for n in graph.nodes]
    colors = [CORE_COLOR if is_core.get(n, False) else OPPONENT_COLOR for n in graph.nodes]
    widths = [(0.3 + 0.4 * graph.edges[e]["n_games"] ** 0.5) * scale ** 0.9
              for e in graph.edges]
    font_size = 10 if width >= 6 else 7

    # figure shape follows the layout, so the network isn't stretched
    xs, ys = zip(*pos.values())
    aspect = (max(ys) - min(ys)) / (max(xs) - min(xs))
    fig, ax = plt.subplots(figsize=(width, max(0.35 * width, width * aspect)),
                           facecolor=BACKGROUND)
    ax.set_aspect("equal")
    ax.set_facecolor(BACKGROUND)
    nx.draw_networkx_edges(graph, pos, ax=ax, width=widths, edge_color=EDGE_COLOR, alpha=0.35)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=sizes, node_color=colors,
                           edgecolors=BACKGROUND, linewidths=0.5 * scale ** 0.5)

    # label the best-connected players, so the hubs can be identified
    if label_top:
        top = sorted(degree, key=degree.get, reverse=True)[:label_top]
        nx.draw_networkx_labels(graph, pos, labels={n: n for n in top}, ax=ax,
                                font_size=font_size - 3, font_color=TEXT_COLOR)

    legend = [Line2D([], [], marker="o", linestyle="", color=CORE_COLOR, label="core player")]
    if not is_core.all():
        legend.append(Line2D([], [], marker="o", linestyle="", color=OPPONENT_COLOR, label=other_label))
    if len(legend) > 1:
        # above the plot, so it never covers a group
        ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2,
                  frameon=False, labelcolor=TEXT_COLOR, fontsize=font_size,
                  handletextpad=0.2, columnspacing=1.5, markerscale=0.6 if width < 6 else 1)

    if title:
        ax.set_title(title, color=TEXT_COLOR, loc="left", fontsize=font_size, pad=20)
    ax.axis("off")
    fig.tight_layout(pad=0.2)
    fig.savefig(out_file, dpi=300, facecolor=BACKGROUND)


    plt.close(fig)
    print(f"Saved {out_file}")


if __name__ == "__main__":
    results = config.ROOT / "results"
    results.mkdir(exist_ok=True)

    graph, players = load_graph(config.PLAYERS_TABLE, config.EDGES_CORE_TABLE)
    plot_network(graph, players,
                 f"Core players: {graph.number_of_nodes()} players, {graph.number_of_edges()} edges",
                 results / "network_core.pdf", label_top=5)

    graph, players = load_graph(config.PLAYERS_ALL_TABLE, config.EDGES_ALL_TABLE)
    plot_network(graph, players,
                 f"All players: {graph.number_of_nodes()} players, {graph.number_of_edges()} edges",
                 results / "network_all.pdf")

    if config.EDGES_SNOWBALL_CORE_TABLE.exists():
        graph, players = load_graph(config.PLAYERS_SNOWBALL_TABLE, config.EDGES_SNOWBALL_CORE_TABLE)
        plot_network(graph, players,
                     f"Core + extension players: {graph.number_of_nodes()} players, "
                     f"{graph.number_of_edges()} edges",
                     results / "network_snowball_core.pdf", other_label="extension player")

    # the same network at print size for the paper (one column of the ACM layout)
    if config.EDGES_SNOWBALL_CORE_TABLE.exists():
        plot_network(graph, players, "", results / "network_snowball_core_paper.pdf",
                     other_label="extension player", width=3.4, arrangement="diagonal")

    if config.EDGES_SNOWBALL_TABLE.exists():
        graph, players = load_graph(config.PLAYERS_ALL_TABLE, config.EDGES_SNOWBALL_TABLE)
        plot_network(graph, players,
                     f"All players, with snowball games: {graph.number_of_nodes()} players, "
                     f"{graph.number_of_edges()} edges",
                     results / "network_snowball.pdf")