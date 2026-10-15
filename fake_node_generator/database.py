import csv
import json
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
from configuration import Configuration
from enum import StrEnum

PROJECT_ROOT = Path(__file__).resolve().parent
RESULT_DIR = PROJECT_ROOT / "result"


class MainTimeControl(StrEnum):
    BLITZ = "blitz"
    RAPID = "rapid"
    BULLET = "bullet"


class PlayerTitle(StrEnum):
    GM = "GM"
    FM = "FM"
    IM = "IM"
    CM = "CM"
    NM = "NM"


class Database:
    configuration: Configuration = None
    graph: nx.Graph | None = None

    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        self.configuration.read_config_data()
        self.planted_subgroups = []
        self.rng = np.random.default_rng(self.configuration.get_global_random_seed())

    def create_graph(self) -> None:
        # create group sizes
        group_sizes = []
        for group in self.configuration.get_groups():
            group_sizes.append(group.number_of_players)

        # create probabilities
        probabilities = []
        number_of_groups = len(self.configuration.get_groups())
        for first_group in range(0, number_of_groups):
            local_probabilities = []
            for second_group in range(0, number_of_groups):
                if first_group == second_group:
                    local_probabilities.append(
                        self.configuration.get_in_group_match_probability()
                    )
                else:
                    local_probabilities.append(
                        self.configuration.get_out_group_match_probability()
                    )
            probabilities.append(local_probabilities)

        # create graph
        first_graph = nx.stochastic_block_model(
            group_sizes,
            probabilities,
            seed=self.configuration.get_sbm_seed(),
        )

        # find largest connected component
        largest_component = max(nx.connected_components(first_graph), key=len)
        self.graph = first_graph.subgraph(largest_component).copy()

    def assign_games_and_distances_to_graph(self) -> None:
        rng = np.random.default_rng(self.configuration.get_sbm_seed())
        for u, v in self.graph.edges():
            same = self.graph.nodes[u].get("block") == self.graph.nodes[v].get("block")
            lamda = (
                self.configuration.get_number_of_games_in_group()
                if same
                else self.configuration.get_number_of_games_out_of_group()
            )
            games = 1 + rng.poisson(lamda)
            self.graph.edges[u, v]["games"] = games
            self.graph.edges[u, v]["distance"] = 1 / games

    def assgin_attributes_to_players(self) -> None:
        for node_id, node_attrs in self.graph.nodes.items():
            # assign title to player
            title_random_chance = self.rng.random()
            if title_random_chance < 0.69:
                node_attrs["title"] = None
            elif title_random_chance >= 0.69 and title_random_chance < 0.87:
                node_attrs["title"] = PlayerTitle.GM
            else:
                titles = [PlayerTitle.IM, PlayerTitle.FM, PlayerTitle.NM, PlayerTitle.CM]
                node_attrs["title"] = titles[self.rng.integers(len(titles))]

            # assign main time control to player
            mc_random_chance = self.rng.random()
            if mc_random_chance < 0.67:
                node_attrs["main_tc"] = MainTimeControl.BLITZ
            elif mc_random_chance >= 0.67 and mc_random_chance < 0.99:
                node_attrs["main_tc"] = MainTimeControl.BULLET
            else:
                node_attrs["main_tc"] = MainTimeControl.RAPID
            # find group attributes
            group_id = node_attrs["block"]
            group = self.configuration.get_groups()[group_id]

            # generate rating for player
            rate = self.rng.normal(group.mean, group.std)
            rate = min(
                max(rate, self.configuration.get_min_rating()),
                self.configuration.get_max_rating(),
            )
            node_attrs["rating"] = round(float(rate))

            # generate target rating for player
            noise = self.rng.normal(0, group.target_std_value)
            target = round(float(group.target_base_line + noise), 1)
            node_attrs["target"] = target

    def plant_subgroup(self) -> None:
        subgroup_size = int(self.configuration.get_sigma())

        self.planted_subgroups = []
        used = set()  # players already in some planted group
        for group in self.configuration.get_groups():  # community 0, 1, 2, 3
            subgroup = 0
            candidates = [
                n
                for n in self.graph.nodes()
                if self.graph.nodes[n]["block"] == group.id
            ]
            if not candidates:
                continue
            for attempt in range(100):
                centre = int(
                    self.rng.choice(candidates)
                )  # select a random node between candidates
                ranking = self._rank_from_center(centre)
                members = [int(n) for n in ranking["player"].head(subgroup_size)]
                if not used & set(members):  # no overlap with earlier groups
                    break
            for n in members:
                self.graph.nodes[n]["target"] += group.target_std_value * 1.0
            used |= set(members)
            self.planted_subgroups.append(
                {
                    "subgroup": subgroup,
                    "group": group.id,
                    "centre": centre,
                    "members": members,
                }
            )

    def calculate_WKL_method_binary_numbers(self) -> None:
        cut = np.quantile(
            [self.graph.nodes[node_id]["target"] for node_id in self.graph.nodes()], 0.8
        )
        for node_id, node_attrs in self.graph.nodes.items():
            node_attrs["WKL_target_bin"] = int(node_attrs["target"] >= cut)

    def _rank_from_center(self, center: int) -> pd.DataFrame:
        if center not in self.graph:
            raise ValueError(f"Node {center} is not in the graph")

        distance = nx.single_source_dijkstra_path_length(
            self.graph, center, weight="distance"
        )
        players = pd.DataFrame.from_dict(
            dict(self.graph.nodes(data=True)), orient="index"
        )
        rows = []
        for player, player_distance in distance.items():
            rows.append(
                {
                    "player": player,
                    "distance": round(player_distance, 9),
                    "gower": self._gower(players, center, player),
                }
            )
        table = pd.DataFrame(rows)
        return table.sort_values(by=["distance", "gower"]).reset_index(drop=True)

    def _gower(self, players: pd.DataFrame, center: int, player: int) -> float:
        num_cols = [col for col in ["rating"] if col in players.columns]
        cat_cols = [col for col in ["main_tc", "title"] if col in players.columns]

        # range of each numeric attribute (max − min) over all players
        ranges = players[num_cols].max() - players[num_cols].min()
        parts = []
        for col in num_cols:
            if ranges[col] == 0:
                parts.append(0)
            else:
                parts.append(
                    abs(players.at[center, col] - players.at[player, col]) / ranges[col]
                )
        for col in cat_cols:
            center_value = players.at[center, col]
            player_value = players.at[player, col]
            if center_value == player_value or (
                pd.isna(center_value) and pd.isna(player_value)
            ):
                parts.append(0)
            else:
                parts.append(1)
        return float(np.mean(parts)) if parts else 0.0

    def _player_names(self) -> dict[int, str]:
        path = PROJECT_ROOT / "confiugrations" / "player.json"
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        return {
            entry["id"]: entry["name"]
            for entry in data
            if isinstance(entry, dict) and "id" in entry and "name" in entry
        }

    def _cell(self, value) -> str | int | float:
        if value is None:
            return ""
        return value.value if hasattr(value, "value") else value

    def save_players(self, result_dir: Path = RESULT_DIR) -> Path:
        if self.graph is None:
            raise RuntimeError("Graph has not been created")

        names = self._player_names()
        result_dir.mkdir(parents=True, exist_ok=True)
        players_path = result_dir / "players.csv"

        with players_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "name",
                    "title",
                    "main_tc",
                    "rating",
                    "target",
                    "group",
                    "WKL_target_bin",
                ]
            )
            for node_id, node_attrs in self.graph.nodes(data=True):
                writer.writerow(
                    [
                        node_id,
                        names.get(node_id, str(node_id)),
                        self._cell(node_attrs.get("title")),
                        self._cell(node_attrs.get("main_tc")),
                        node_attrs.get("rating", ""),
                        node_attrs.get("target", ""),
                        node_attrs.get("block", ""),
                        node_attrs.get("WKL_target_bin", ""),
                    ]
                )

        return players_path

    def save_edges(self, result_dir: Path = RESULT_DIR) -> Path:
        if self.graph is None:
            raise RuntimeError("Graph has not been created")

        names = self._player_names()
        result_dir.mkdir(parents=True, exist_ok=True)
        edges_path = result_dir / "edges.csv"

        with edges_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "player_a_name",
                    "player_b_name",
                    "games",
                    "distance",
                    "player_a_group",
                    "player_b_group",
                ]
            )
            for player_a, player_b, edge_attrs in self.graph.edges(data=True):
                writer.writerow(
                    [
                        names.get(player_a, str(player_a)),
                        names.get(player_b, str(player_b)),
                        edge_attrs.get("games", 0),
                        edge_attrs.get("distance", ""),
                        self.graph.nodes[player_a].get("block", ""),
                        self.graph.nodes[player_b].get("block", ""),
                    ]
                )

        return edges_path

    def save_planted_subgroups(self, result_dir: Path = RESULT_DIR) -> Path:
        if not self.planted_subgroups:
            raise RuntimeError("No planted subgroups; call plant_subgroup() first")

        names = self._player_names()
        result_dir.mkdir(parents=True, exist_ok=True)
        subgroups_path = result_dir / "planted_subgroups.csv"

        with subgroups_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["player_id", "username", "group", "centre"])
            for subgroup in self.planted_subgroups:
                for player_id in subgroup["members"]:
                    writer.writerow(
                        [
                            player_id,
                            names.get(player_id, str(player_id)),
                            subgroup["group"],
                            subgroup["centre"],
                        ]
                    )

        return subgroups_path
