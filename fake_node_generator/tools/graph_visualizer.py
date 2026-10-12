from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import Circle, Polygon

from models.group import Group

GROUP_COLORS = [
    "#d62728",  # red
    "#1f77b4",  # blue
    "#222222",  # black
    "#2ca02c",  # green
    "#ff7f0e",  # orange
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#17becf",  # cyan
    "#bcbd22",  # olive
]
UNKNOWN_GROUP_COLOR = "#9aa0a6"
CROSS_GROUP_EDGE_COLOR = "#b0b7c3"
SUBGROUP_RING_COLOR = "#ffbf00"


def visualize_graph(
    graph: nx.Graph,
    groups: list[Group] | None = None,
    planted_subgroups: list[dict] | None = None,
    save_path: str | Path | None = None,
    show: bool = True,
    seed: int | None = None,
    node_size: float = 30,
    edge_width: float = 1.5,
    edge_alpha: float = 0.6,
    show_edge_labels: bool = True,
    edge_label_font_size: float = 7.0,
) -> None:
    """Draw the graph built by `Database.create_graph`.

    Nodes are colored by the `block` attribute that `nx.stochastic_block_model`
    stores on each node. `block` is the index of the group in `groups`, so when
    `groups` is given the legend shows the group names.

    When `Database.assign_games_and_distances_to_graph` has run, each edge has
    `games` and `distance` attributes: edges get thicker with more games, pairs
    with more games are pulled closer in the layout, and each edge is labeled
    with its games and distance.

    `planted_subgroups` is `Database.planted_subgroups`. Each subgroup is shaded
    in its group's color, its members get a gold ring and its centre is a star.
    """
    blocks = sorted({data["block"] for _, data in graph.nodes(data=True) if "block" in data})
    color_of = {block: _group_color(index) for index, block in enumerate(blocks)}

    has_games = graph.number_of_edges() > 0 and all("games" in data for _, _, data in graph.edges(data=True))
    max_games = max((data["games"] for _, _, data in graph.edges(data=True)), default=1) if has_games else 1

    def width_of(edges: list[tuple[int, int]]) -> list[float]:
        if not has_games:
            return [edge_width] * len(edges)
        return [edge_width * (0.4 + graph.edges[edge]["games"] / max_games) for edge in edges]

    positions = nx.spring_layout(graph, seed=seed, weight="games" if has_games else None)
    figure, axis = plt.subplots(figsize=(14, 14))

    in_group_edges, cross_group_edges = [], []
    for left, right in graph.edges:
        left_block = graph.nodes[left].get("block")
        if left_block is not None and left_block == graph.nodes[right].get("block"):
            in_group_edges.append((left, right))
        else:
            cross_group_edges.append((left, right))

    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=cross_group_edges,
        edge_color=CROSS_GROUP_EDGE_COLOR,
        alpha=edge_alpha * 0.6,
        width=width_of(cross_group_edges),
        ax=axis,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=in_group_edges,
        edge_color=[color_of[graph.nodes[left]["block"]] for left, _ in in_group_edges],
        alpha=edge_alpha,
        width=width_of(in_group_edges),
        ax=axis,
    )
    if has_games and show_edge_labels:
        nx.draw_networkx_edge_labels(
            graph,
            positions,
            edge_labels={
                (left, right): f"{data['games']} | {data['distance']:.2f}"
                for left, right, data in graph.edges(data=True)
            },
            font_size=edge_label_font_size,
            font_color="#333333",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.8},
            ax=axis,
        )

    subgroups = [
        subgroup
        for subgroup in planted_subgroups or []
        if any(member in graph for member in subgroup["members"])
    ]
    for subgroup in subgroups:
        _draw_subgroup_area(
            axis,
            [positions[member] for member in subgroup["members"] if member in graph],
            color_of.get(subgroup["group"], UNKNOWN_GROUP_COLOR),
        )

    def node_color(node: int):
        return color_of.get(graph.nodes[node].get("block"), UNKNOWN_GROUP_COLOR)

    planted = {member for subgroup in subgroups for member in subgroup["members"]}
    centres = {subgroup["centre"] for subgroup in subgroups if subgroup["centre"] in graph}
    other_nodes = [node for node in graph.nodes if node not in planted]
    member_nodes = [node for node in graph.nodes if node in planted and node not in centres]
    centre_nodes = [node for node in graph.nodes if node in centres]

    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=other_nodes,
        node_color=[node_color(node) for node in other_nodes],
        node_size=node_size,
        edgecolors="white",
        linewidths=0.5,
        ax=axis,
    )
    if member_nodes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=member_nodes,
            node_color=[node_color(node) for node in member_nodes],
            node_size=node_size * 2.5,
            edgecolors=SUBGROUP_RING_COLOR,
            linewidths=2,
            ax=axis,
        )
    if centre_nodes:
        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=centre_nodes,
            node_color=[node_color(node) for node in centre_nodes],
            node_size=node_size * 9,
            node_shape="*",
            edgecolors=SUBGROUP_RING_COLOR,
            linewidths=1.5,
            ax=axis,
        )

    if blocks:
        handles = [
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=color_of[block],
                markeredgecolor="white",
                markersize=9,
                label=_group_label(block, groups, graph),
            )
            for block in blocks
        ]
        if subgroups:
            handles += [
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="none",
                    markerfacecolor="white",
                    markeredgecolor=SUBGROUP_RING_COLOR,
                    markeredgewidth=2,
                    markersize=9,
                    label="Planted subgroup member",
                ),
                plt.Line2D(
                    [0],
                    [0],
                    marker="*",
                    color="none",
                    markerfacecolor="white",
                    markeredgecolor=SUBGROUP_RING_COLOR,
                    markersize=15,
                    label="Planted subgroup centre",
                ),
            ]
        axis.legend(
            handles=handles,
            loc="upper left",
            frameon=False,
            title="Edge labels: games | distance" if has_games and show_edge_labels else None,
            title_fontsize=9,
            alignment="left",
        )

    title = f"Player graph ({graph.number_of_nodes()} players, {graph.number_of_edges()} connections"
    if has_games:
        title += f", {sum(data['games'] for _, _, data in graph.edges(data=True))} games"
    if subgroups:
        title += f", {len(subgroups)} planted subgroups"
    axis.set_title(title + ")")
    axis.set_aspect("equal")
    axis.axis("off")
    figure.tight_layout()

    if save_path is not None:
        figure.savefig(save_path, dpi=200)
    if show:
        plt.show()
    else:
        plt.close(figure)


def _draw_subgroup_area(axis, points: list, color, padding: float = 0.06) -> None:
    points = np.asarray(points, dtype=float)
    centroid = points.mean(axis=0)
    style = {"facecolor": color, "edgecolor": color, "alpha": 0.18, "linewidth": 2, "zorder": 0}

    hull = _convex_hull(points)
    if len(hull) < 3:
        radius = max(np.linalg.norm(points - centroid, axis=1).max(), 0) + padding
        axis.add_patch(Circle(centroid, radius, **style))
        return

    offsets = hull - centroid
    lengths = np.maximum(np.linalg.norm(offsets, axis=1, keepdims=True), 1e-9)
    axis.add_patch(Polygon(hull + offsets / lengths * padding, closed=True, **style))


def _convex_hull(points: np.ndarray) -> np.ndarray:
    unique = sorted({(float(x), float(y)) for x, y in points})
    if len(unique) < 3:
        return np.array(unique)

    def cross(o, a, b) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.array(lower[:-1] + upper[:-1])


def _group_color(index: int):
    if index < len(GROUP_COLORS):
        return GROUP_COLORS[index]
    return plt.get_cmap("tab20")(index % 20)


def _group_label(block: int, groups: list[Group] | None, graph: nx.Graph) -> str:
    size = sum(1 for _, data in graph.nodes(data=True) if data.get("block") == block)
    name = groups[block].name if groups is not None and block < len(groups) else f"Group {block}"
    return f"{name} ({size} players)"
