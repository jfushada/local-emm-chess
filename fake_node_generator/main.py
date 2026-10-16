"""Generate a range of networks, from obvious planted subgroups to hard ones.

For every combination of shift strength (in target sd) and subgroup size from
`network_range` in config.json, one network is generated with the same
planted subgroup setting in every group. The graph, ratings and targets come
from the same seeds in every run, so only the planted subgroups differ.

Each network is saved in result/network_range/shift_<shift>_size_<size>/ and
result/network_range/networks.csv lists all of them.
"""

import csv
import warnings
from pathlib import Path

from database import Database, RESULT_DIR
from configuration import Configuration
from models.planted_subgroup import PlantedSubgroup
from tools.graph_visualizer import visualize_graph

RANGE_DIR = RESULT_DIR / "network_range"


def generate_network(
    configuration: Configuration, result_dir: Path = RESULT_DIR, show: bool = True
) -> Database:
    main_db = Database(configuration=configuration)
    main_db.create_graph()
    main_db.assign_games_and_distances_to_graph()
    main_db.assgin_attributes_to_players()
    main_db.plant_subgroup()
    main_db.calculate_WKL_method_binary_numbers()
    main_db.save_players(result_dir)
    main_db.save_edges(result_dir)
    main_db.save_planted_subgroups(result_dir)

    visualize_graph(
        main_db.graph,
        groups=configuration.get_groups(),
        planted_subgroups=main_db.planted_subgroups,
        seed=configuration.get_sbm_seed(),
        show_edge_labels=False,
        save_path=result_dir / "graph.png",
        show=show,
    )
    return main_db


def main():
    base_configuration = Configuration()
    base_configuration.read_config_data()
    groups = base_configuration.get_groups()

    rows = []
    for shift_strength in base_configuration.get_range_shift_strengths():
        for subgroup_size in base_configuration.get_range_subgroup_sizes():
            for group in groups:
                if subgroup_size >= group.number_of_players:
                    warnings.warn(
                        f"Subgroup size {subgroup_size} is not smaller than "
                        f"{group.name} ({group.number_of_players} players); the "
                        f"subgroup covers the whole group or spills into other groups"
                    )

            configuration = Configuration()
            configuration.read_config_data()
            configuration.set_planted_subgroups(
                [
                    PlantedSubgroup(
                        group=group.id,
                        sigma=subgroup_size,
                        shift_strength=shift_strength,
                    )
                    for group in groups
                ]
            )

            name = f"shift_{shift_strength:g}_size_{subgroup_size}"
            result_dir = RANGE_DIR / name
            result_dir.mkdir(parents=True, exist_ok=True)
            print(f"Generating {name}")
            database = generate_network(configuration, result_dir, show=False)

            rows.append(
                [
                    name,
                    shift_strength,
                    subgroup_size,
                    len(database.planted_subgroups),
                    sum(len(subgroup["members"]) for subgroup in database.planted_subgroups),
                    database.graph.number_of_nodes(),
                ]
            )

    with (RANGE_DIR / "networks.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "network",
                "shift_strength_sd",
                "subgroup_size",
                "planted_subgroups",
                "planted_players",
                "players",
            ]
        )
        writer.writerows(rows)


if __name__ == "__main__":
    main()
