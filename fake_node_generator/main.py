from database import Database, RESULT_DIR
from configuration import Configuration
from tools.graph_visualizer import visualize_graph


def main():
    configuration = Configuration()
    main_db = Database(configuration=configuration)
    main_db.create_graph()
    main_db.assign_games_and_distances_to_graph()
    main_db.assgin_attributes_to_players()
    main_db.plant_subgroup()
    main_db.calculate_WKL_method_binary_numbers()
    main_db.save_players()
    main_db.save_edges()
    main_db.save_planted_subgroups()

    visualize_graph(
        main_db.graph,
        groups=configuration.get_groups(),
        planted_subgroups=main_db.planted_subgroups,
        seed=configuration.get_sbm_seed(),
        show_edge_labels=False,
        save_path=RESULT_DIR / "graph.png",
    )


if __name__ == "__main__":
    main()
