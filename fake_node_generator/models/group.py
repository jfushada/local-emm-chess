from dataclasses import dataclass, field


@dataclass(frozen=False)
class Group:
    name: str | None = None
    id: int | None = None
    mean: float | None = None
    std: float | None = None
    number_of_players: int = 0
    target_base_line: float | None = None
    target_std_value: float | None = None
