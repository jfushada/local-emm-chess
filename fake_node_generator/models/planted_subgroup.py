from dataclasses import dataclass


@dataclass(frozen=False)
class PlantedSubgroup:
    group: int | None = None
    sigma: int = 0
    shift_strength: float = 0.0
