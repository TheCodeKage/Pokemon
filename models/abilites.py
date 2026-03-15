from dataclasses import dataclass


@dataclass(frozen=True)
class Ability:
    name: str
    effect: str
