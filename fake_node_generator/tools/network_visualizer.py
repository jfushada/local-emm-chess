from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea

from models.edge import Edge
from models.player import Player

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
DEFAULT_NODE_COLOR = "#3b6ea5"
UNKNOWN_GROUP_COLOR = "#9aa0a6"
CROSS_GROUP_EDGE_COLOR = "#b0b7c3"


def visualize_network(
    edges: list[Edge],
    save_path: str | Path | None = None,
    show: bool = True,
    min_games: int = 1,
    show_edge_labels: bool = True,
    label_font_size: float = 8.0,
    edge_label_font_size: float = 4.0,
) -> None:
    """Draw the player network built by `Database.create_edges`.

    Only edges with at least `min_games` games are drawn. Each drawn edge is
    labeled with its `n_games` at its midpoint, and its width grows with
    `n_games`. Nodes and in-group edges are colored by `Player.group`, and each
    node is labeled with its total games against every group: its own group
    first, then the other groups, each number drawn in that group's color.
    """
    players = _players_by_id(edges)
    drawn_edges = [edge for edge in edges if edge.n_games >= max(min_games, 1)]
    node_ids = sorted(players)
    positions = _spring_layout(node_ids, drawn_edges)

    groups = {player_id: player.group for player_id, player in players.items() if player.group is not None}
    group_ids = sorted(set(groups.values()))
    color_of = _group_color_map(group_ids)

    figure, axis = plt.subplots(figsize=(14, 14))
    _draw_edges(axis, drawn_edges, positions, groups, color_of)
    if show_edge_labels:
        _draw_edge_labels(axis, drawn_edges, positions, edge_label_font_size)

    if node_ids:
        coordinates = np.array([positions[node_id] for node_id in node_ids])
        if groups:
            colors = [color_of.get(groups.get(node_id), UNKNOWN_GROUP_COLOR) for node_id in node_ids]
        else:
            colors = [DEFAULT_NODE_COLOR] * len(node_ids)
        axis.scatter(
            coordinates[:, 0],
            coordinates[:, 1],
            s=40,
            c=colors,
            edgecolors="white",
            linewidths=0.5,
            zorder=3,
        )
        if groups:
            _draw_group_game_counts(axis, drawn_edges, node_ids, positions, groups, group_ids, color_of, label_font_size)
            _add_group_legend(axis, group_ids, color_of)

    total_games = sum(edge.n_games for edge in drawn_edges)
    axis.set_title(
        f"Player network ({len(node_ids)} players, {len(drawn_edges)} connections, {total_games} games)"
    )
    axis.set_aspect("equal")
    axis.margins(0.06)
    axis.axis("off")
    figure.tight_layout()

    if save_path is not None:
        figure.savefig(save_path, dpi=200)
    if show:
        plt.show()
    else:
        plt.close(figure)


def _players_by_id(edges: list[Edge]) -> dict[int, Player]:
    players: dict[int, Player] = {}
    for edge in edges:
        for player in (edge.player_a, edge.player_b):
            if player is not None and player.id is not None:
                players[player.id] = player
    return players


def _group_color_map(group_ids: list[int]) -> dict[int, str | tuple]:
    if len(group_ids) <= len(GROUP_COLORS):
        return {group_id: GROUP_COLORS[index] for index, group_id in enumerate(group_ids)}
    palette = plt.get_cmap("tab20")
    return {group_id: palette(index % 20) for index, group_id in enumerate(group_ids)}


def _draw_edges(axis, edges: list[Edge], positions, groups, color_of) -> None:
    if not edges:
        return

    max_games = max(edge.n_games for edge in edges)
    cross_segments, cross_colors, cross_widths = [], [], []
    inner_segments, inner_colors, inner_widths = [], [], []
    for edge in edges:
        left, right = edge.player_a.id, edge.player_b.id
        segment = [positions[left], positions[right]]
        width = 0.2 + 1.6 * edge.n_games / max_games
        left_group = groups.get(left)
        if left_group is not None and left_group == groups.get(right):
            inner_segments.append(segment)
            inner_colors.append(to_rgba(color_of[left_group], 0.28))
            inner_widths.append(width)
        else:
            cross_segments.append(segment)
            cross_colors.append(to_rgba(CROSS_GROUP_EDGE_COLOR, 0.15 if groups else 0.35))
            cross_widths.append(width)

    axis.add_collection(
        LineCollection(
            cross_segments + inner_segments,
            colors=cross_colors + inner_colors,
            linewidths=cross_widths + inner_widths,
            zorder=1,
        )
    )


def _draw_edge_labels(axis, edges: list[Edge], positions, font_size: float) -> None:
    for edge in edges:
        midpoint = (positions[edge.player_a.id] + positions[edge.player_b.id]) / 2
        axis.text(
            midpoint[0],
            midpoint[1],
            str(edge.n_games),
            fontsize=font_size,
            color="#444444",
            ha="center",
            va="center",
            zorder=2,
        )


def _draw_group_game_counts(
    axis,
    edges: list[Edge],
    node_ids: list[int],
    positions: dict[int, np.ndarray],
    groups: dict[int, int],
    group_ids: list[int],
    color_of: dict,
    font_size: float,
) -> None:
    outline = [patheffects.withStroke(linewidth=1.2, foreground="white")]

    games_against: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for edge in edges:
        left, right = edge.player_a.id, edge.player_b.id
        if right in groups:
            games_against[left][groups[right]] += edge.n_games
        if left in groups:
            games_against[right][groups[left]] += edge.n_games

    for node_id in node_ids:
        own_group = groups.get(node_id)
        if own_group is None:
            continue

        ordered_groups = [own_group] + [group_id for group_id in group_ids if group_id != own_group]
        numbers = [
            TextArea(
                str(games_against[node_id][group_id]),
                textprops={
                    "color": color_of[group_id],
                    "fontsize": font_size,
                    "fontweight": "bold",
                    "path_effects": outline,
                },
            )
            for group_id in ordered_groups
        ]
        axis.add_artist(
            AnnotationBbox(
                HPacker(children=numbers, align="center", pad=0, sep=1.5),
                positions[node_id],
                xybox=(3.5, 0),
                xycoords="data",
                boxcoords="offset points",
                box_alignment=(0, 0.5),
                frameon=False,
                zorder=4,
            )
        )


def _add_group_legend(axis, group_ids: list[int], color_of: dict) -> None:
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=color_of[group_id],
            markeredgecolor="white",
            markersize=8,
            label=f"Group {group_id}",
        )
        for group_id in group_ids
    ]
    axis.legend(
        handles=handles,
        loc="upper left",
        frameon=False,
        title="Numbers on edges: games between the two players\n"
        "Numbers beside a node: games against its\nown group first, then against each other group",
        title_fontsize=8,
        alignment="left",
    )


def _spring_layout(node_ids: list[int], edges: list[Edge]) -> dict[int, np.ndarray]:
    count = len(node_ids)
    if count == 0:
        return {}
    if count == 1:
        return {node_ids[0]: np.zeros(2)}

    rng = np.random.default_rng(0)
    positions = rng.random((count, 2))
    index_of = {node_id: index for index, node_id in enumerate(node_ids)}
    edge_index = (
        np.array([(index_of[edge.player_a.id], index_of[edge.player_b.id]) for edge in edges], dtype=int)
        if edges
        else np.empty((0, 2), dtype=int)
    )
    # pairs that played more games are pulled closer together
    weights = np.array([edge.n_games for edge in edges], dtype=float)
    if len(weights):
        weights /= weights.mean()
    ideal_distance = float(np.sqrt(1.0 / count))
    temperature = 0.12

    for _ in range(60):
        delta = positions[:, None, :] - positions[None, :, :]
        distance = np.maximum(np.linalg.norm(delta, axis=2), 1e-6)
        np.fill_diagonal(distance, np.inf)
        direction = delta / distance[..., None]
        repulsion = (ideal_distance**2 / distance)[..., None] * direction
        displacement = repulsion.sum(axis=1)

        if len(edge_index):
            attraction_delta = positions[edge_index[:, 0]] - positions[edge_index[:, 1]]
            attraction_distance = np.maximum(np.linalg.norm(attraction_delta, axis=1), 1e-6)
            attraction = (weights * attraction_distance**2 / ideal_distance)[:, None] * (
                attraction_delta / attraction_distance[:, None]
            )
            np.add.at(displacement, edge_index[:, 0], -attraction)
            np.add.at(displacement, edge_index[:, 1], attraction)

        step_length = np.linalg.norm(displacement, axis=1)
        safe_length = np.maximum(step_length, 1e-6)
        positions += (displacement / safe_length[:, None]) * np.minimum(step_length, temperature)[:, None]
        temperature *= 0.9

    positions -= positions.mean(axis=0)
    scale = np.max(np.abs(positions))
    if scale > 0:
        positions /= scale
    return {node_id: positions[index] for index, node_id in enumerate(node_ids)}
