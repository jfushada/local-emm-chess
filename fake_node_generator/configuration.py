import json
from pathlib import Path

from models.group import Group


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "confiugrations"


class Configuration:
    def __init__(self, config_dir: Path = CONFIG_DIR) -> None:
        self.config_path = config_dir / "config.json"
        self._in_group_match_probability: float | None = None
        self._out_group_match_probability: float | None = None
        self._max_number_of_games_between_two_player: int | None = None
        self._player_target_std_value: float | None = None
        self._player_target_mean_value: float | None = None
        self._groups: list[Group] | None = None
        self._sbm_seed: int | None = None
        self._global_random_seed: int | None = None
        self._number_of_games_in_group: int | None = None
        self._number_of_games_out_of_group: int | None = None
        self._sigma: float | None = None
        self._shift_strength: float | None = None
        self._min_rating: int | None = None
        self._max_rating: int | None = None

    def read_config_data(self) -> None:
        # read all of the configuration data from the config.json file and assign it to the class variables
        data = self._load_json(self.config_path)
        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object in {self.config_path}")

        self._in_group_match_probability = self._require_probability(
            data, "in_group_match_probability"
        )
        self._out_group_match_probability = self._require_probability(
            data, "out_group_match_probability"
        )
        self._max_number_of_games_between_two_player = self._require_positive_int(
            data, "max_number_of_games_between_two_player"
        )
        self._player_target_std_value = self._require_positive_float(
            data, "player_target_std_value"
        )
        self._player_target_mean_value = self._require_positive_float(
            data, "player_target_mean_value"
        )
        self._sbm_seed = self._require_non_negative_int(data, "SBM_seed")
        self._global_random_seed = self._require_non_negative_int(
            data, "global_random_seed"
        )
        self._number_of_games_in_group = self._require_positive_int(
            data, "number_of_games_in_group"
        )
        self._number_of_games_out_of_group = self._require_non_negative_int(
            data, "number_of_games_out_of_group"
        )
        self._sigma = self._require_positive_float(data, "sigma")
        self._shift_strength = self._require_positive_float(data, "shift_strength")
        self._min_rating = self._require_positive_int(data, "min_rating")
        self._max_rating = self._require_positive_int(data, "max_rating")
        if self._min_rating > self._max_rating:
            raise ValueError(
                f"'min_rating' in {self.config_path} must not be greater than 'max_rating'"
            )
        self._groups = self._require_groups(data, "groups")

    def get_in_group_match_probability(self) -> float:
        if self._in_group_match_probability is None:
            self.read_config_data()
        return self._in_group_match_probability

    def get_out_group_match_probability(self) -> float:
        if self._out_group_match_probability is None:
            self.read_config_data()
        return self._out_group_match_probability

    def get_max_number_of_games_between_two_player(self) -> int:
        if self._max_number_of_games_between_two_player is None:
            self.read_config_data()
        return self._max_number_of_games_between_two_player

    def get_player_target_std_value(self) -> float:
        if self._player_target_std_value is None:
            self.read_config_data()
        return self._player_target_std_value

    def get_player_target_mean_value(self) -> float:
        if self._player_target_mean_value is None:
            self.read_config_data()
        return self._player_target_mean_value

    def get_groups(self) -> list[Group]:
        if self._groups is None:
            self.read_config_data()
        return self._groups

    def get_sbm_seed(self) -> int:
        if self._sbm_seed is None:
            self.read_config_data()
        return self._sbm_seed

    def get_global_random_seed(self) -> int:
        if self._global_random_seed is None:
            self.read_config_data()
        return self._global_random_seed

    def get_number_of_games_in_group(self) -> int:
        if self._number_of_games_in_group is None:
            self.read_config_data()
        return self._number_of_games_in_group

    def get_number_of_games_out_of_group(self) -> int:
        if self._number_of_games_out_of_group is None:
            self.read_config_data()
        return self._number_of_games_out_of_group

    def get_sigma(self) -> float:
        if self._sigma is None:
            self.read_config_data()
        return self._sigma

    def get_shift_strength(self) -> float:
        if self._shift_strength is None:
            self.read_config_data()
        return self._shift_strength

    def get_min_rating(self) -> int:
        if self._min_rating is None:
            self.read_config_data()
        return self._min_rating

    def get_max_rating(self) -> int:
        if self._max_rating is None:
            self.read_config_data()
        return self._max_rating

    def _require_positive_int(self, data: dict, key: str) -> int:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(
                f"'{key}' in {self.config_path} must be a positive integer"
            )
        return value

    def _require_non_negative_int(self, data: dict, key: str) -> int:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                f"'{key}' in {self.config_path} must be a non-negative integer"
            )
        return value

    def _require_probability(self, data: dict, key: str) -> float:
        value = data.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 1
        ):
            raise ValueError(
                f"'{key}' in {self.config_path} must be a number between 0 and 1"
            )
        return float(value)

    def _require_positive_float(self, data: dict, key: str) -> float:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"'{key}' in {self.config_path} must be a positive float")
        return float(value)

    def _require_groups(self, data: dict, key: str) -> list[Group]:
        value = data.get(key)
        if not isinstance(value, list):
            raise ValueError(f"'{key}' in {self.config_path} must be a list")

        groups: list[Group] = []
        seen_ids: set[int] = set()
        seen_names: set[str] = set()

        for index, entry in enumerate(value):
            where = f"'{key}[{index}]' in {self.config_path}"
            if not isinstance(entry, dict):
                raise ValueError(f"{where} must be an object")

            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{where} must have a non-empty string 'name'")
            if name in seen_names:
                raise ValueError(f"{where} has duplicate name '{name}'")
            seen_names.add(name)

            group_id = entry.get("id")
            if (
                isinstance(group_id, bool)
                or not isinstance(group_id, int)
                or group_id < 0
            ):
                raise ValueError(f"{where} must have a non-negative integer 'id'")
            if group_id in seen_ids:
                raise ValueError(f"{where} has duplicate id {group_id}")
            seen_ids.add(group_id)

            mean = entry.get("mean")
            if isinstance(mean, bool) or not isinstance(mean, (int, float)):
                raise ValueError(f"{where} must have a numeric 'mean'")

            std = entry.get("std")
            if isinstance(std, bool) or not isinstance(std, (int, float)) or std < 0:
                raise ValueError(f"{where} must have a non-negative numeric 'std'")

            number_of_players = entry.get("number_of_players")
            if (
                isinstance(number_of_players, bool)
                or not isinstance(number_of_players, int)
                or number_of_players < 1
            ):
                raise ValueError(
                    f"{where} must have a positive integer 'number_of_players'"
                )

            target_base_line = entry.get("target_base_line")
            if isinstance(target_base_line, bool) or not isinstance(
                target_base_line, (int, float)
            ):
                raise ValueError(f"{where} must have a numeric 'target_base_line'")

            target_std_value = entry.get("target_std_value")
            if (
                isinstance(target_std_value, bool)
                or not isinstance(target_std_value, (int, float))
                or target_std_value < 0
            ):
                raise ValueError(
                    f"{where} must have a non-negative numeric 'target_std_value'"
                )

            groups.append(
                Group(
                    name=name,
                    id=group_id,
                    mean=float(mean),
                    std=float(std),
                    number_of_players=number_of_players,
                    target_base_line=float(target_base_line),
                    target_std_value=float(target_std_value),
                )
            )

        return groups

    @staticmethod
    def _load_json(path: Path):
        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Configuration file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
