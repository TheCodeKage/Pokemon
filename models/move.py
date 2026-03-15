from dataclasses import dataclass, field
from models import Type, DamageClass


@dataclass(frozen=True)
class BaseMove:
    name: str
    type: Type
    power: int
    accuracy: int
    pp: int
    damage_class: DamageClass
    effect_chance: int = 0
    effect_entry: str = ""

@dataclass
class Move:
    base_move: BaseMove
    current_pp: int = field(init=False,)

    def __post_init__(self):
        self.current_pp = self.base_move.pp

    def use(self):
        if self.current_pp <= 0:
            raise ValueError(f"{self.base_move.name} has no PP left")
        self.current_pp -= 1

    @property
    def name(self):
        return self.base_move.name