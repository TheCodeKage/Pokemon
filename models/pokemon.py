import random
from dataclasses import dataclass, fields, field
from typing import List, Optional

from models.abilites import Ability
from models.move import BaseMove, Move
from models.enums import StatusCondition, Type, VolatileCondition


@dataclass(frozen=True)
class Stats:
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int


@dataclass(frozen=True)
class PokemonSpecies:
    name: str
    stats: Stats
    types: list[Type]
    moves: list[BaseMove]
    abilities: list[Ability]


@dataclass
class Pokemon:
    species: PokemonSpecies
    moves: List[BaseMove]
    IVs: Stats
    EVs: Stats
    ability: Ability
    level: int
    name: str = field(default="")

    def calculate_stat(self, base: int, iv: int, ev: int, is_hp: bool = False) -> int:
        """Calculate actual stat value using Pokemon formula"""
        if is_hp:
            return ((2 * base + iv + ev // 4) * self.level // 100) + self.level + 10
        else:
            return ((2 * base + iv + ev // 4) * self.level // 100) + 5

    @property
    def max_hp(self) -> int:
        return self.calculate_stat(self.species.stats.hp, self.IVs.hp, self.EVs.hp, is_hp=True)

    @property
    def attack(self) -> int:
        return self.calculate_stat(self.species.stats.attack, self.IVs.attack, self.EVs.attack)

    @property
    def defense(self) -> int:
        return self.calculate_stat(self.species.stats.defense, self.IVs.defense, self.EVs.defense)

    @property
    def special_attack(self) -> int:
        return self.calculate_stat(self.species.stats.special_attack, self.IVs.special_attack, self.EVs.special_attack)

    @property
    def special_defense(self) -> int:
        return self.calculate_stat(self.species.stats.special_defense, self.IVs.special_defense, self.EVs.special_defense)

    @property
    def speed(self) -> int:
        return self.calculate_stat(self.species.stats.speed, self.IVs.speed, self.EVs.speed)

    def __post_init__(self):
        if len(self.moves) > 4:
            raise ValueError("A pokemon can only learn 4 moves")

        for move in self.moves:
            if move not in self.species.moves:
                raise ValueError(f"{self.species.name} can not learn {move}")

        if self.ability not in self.species.abilities:
            raise ValueError(f"{self.species.name} can not have {self.ability}")

        for f in fields(self.IVs):
            iv = getattr(self.IVs, f.name)
            ev = getattr(self.EVs, f.name)

            if not (0 <= iv <= 31):
                raise ValueError(f"IV for {f.name} must be between 0 and 31 (got {iv})")

            if not (0 <= ev <= 252):
                raise ValueError(f"EV for {f.name} must be between 0 and 252 (got {ev})")

        total_evs = sum(getattr(self.EVs, f.name) for f in fields(self.EVs))

        if total_evs > 510:
            raise ValueError(f"Total EVs cannot exceed 510 (got {total_evs})")

        if not (1 <= self.level <= 100):
            raise ValueError(f"Level must be between 1 and 100 (got {self.level})")

        max_hp = self.max_hp

        if len(set(self.moves)) != len(self.moves):
            raise ValueError("Pokemon cannot have duplicate moves")

        if self.name == "":
            self.name = self.species.name


@dataclass
class BattlePokemon:
    pokemon: Pokemon
    stat_changes: Stats = field(
        default_factory=lambda: Stats(0, 0, 0, 0, 0, 0)
    )
    volatile_conditions: List[VolatileCondition] = field(default_factory=list)
    status_condition: Optional[StatusCondition] = None
    toxic_counter: int = 0
    sleep_counter: int = 0
    moves: List[Move] = field(default_factory=list, init=False)
    current_hp: int = field(default=-1)

    def __post_init__(self):
        for f in fields(self.stat_changes):
            if getattr(self.stat_changes, f.name) > 6 or getattr(self.stat_changes, f.name) < -6:
                raise ValueError(f"Stat change for {f.name} must be between +6 & -6 (got {getattr(self.stat_changes, f.name)})")

        if self.status_condition is not None and not isinstance(self.status_condition, StatusCondition):
            raise ValueError("status_condition must be a StatusCondition")

        for move in self.pokemon.moves:
            self.moves.append(Move(move))

        if self.current_hp == -1:
            self.current_hp = self.pokemon.max_hp
        elif self.current_hp < 0:
            raise ValueError("current_hp cannot be negative")

        if self.current_hp > self.pokemon.max_hp:
            raise ValueError(f"current_hp cannot exceed max HP ({self.pokemon.max_hp})")

    @property
    def name(self):
        return self.pokemon.name

    def get_stat_multiplier(self, stage: int) -> float:
        """Get stat multiplier based on stage (-6 to +6)"""
        if stage >= 0:
            return (2 + stage) / 2
        else:
            return 2 / (2 - stage)

    @property
    def attack(self) -> int:
        base = int(self.pokemon.attack * self.get_stat_multiplier(self.stat_changes.attack))
        if self.status_condition == StatusCondition.BURN:
            return base // 2
        return base

    @property
    def defense(self) -> int:
        return int(self.pokemon.defense * self.get_stat_multiplier(self.stat_changes.defense))

    @property
    def special_attack(self) -> int:
        return int(self.pokemon.special_attack * self.get_stat_multiplier(self.stat_changes.special_attack))

    @property
    def special_defense(self) -> int:
        return int(self.pokemon.special_defense * self.get_stat_multiplier(self.stat_changes.special_defense))

    @property
    def speed(self) -> int:
        base = int(self.pokemon.speed * self.get_stat_multiplier(self.stat_changes.speed))
        if self.status_condition == StatusCondition.PARALYSIS:
            return base // 2
        return base

    def switch_out(self):
        self.stat_changes = Stats(0, 0, 0, 0, 0, 0)
        self.volatile_conditions.clear()
        self.toxic_counter = 0
        # status_condition intentionally persists through switching

    def apply_status(self, condition: StatusCondition):
        if self.status_condition is not None:
            return
        # Type immunities
        if condition == StatusCondition.FREEZE and Type.ICE in self.pokemon.species.types:
            return
        if condition == StatusCondition.BURN and Type.FIRE in self.pokemon.species.types:
            return
        if condition == StatusCondition.POISON and (
                Type.POISON in self.pokemon.species.types
                or Type.STEEL in self.pokemon.species.types
        ):
            return
        self.status_condition = condition
        if condition == StatusCondition.SLEEP:
            self.sleep_counter = random.randint(1, 3)
