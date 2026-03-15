from dataclasses import dataclass, field
from models.pokemon import Pokemon, BattlePokemon


@dataclass
class Trainer:
    name: str
    trainer_id: int
    pokemon: list[Pokemon]

    def __post_init__(self):
        if len(self.pokemon) > 6:
            raise ValueError("A trainer can only have 6 Pokemon")
        if len(set(self.pokemon)) != len(self.pokemon):
            raise ValueError("Trainer cannot have duplicate Pokemon")
        if len(self.pokemon) < 1:
            raise ValueError("Trainer must have at least 1 Pokemon")


@dataclass
class BattleTrainer:
    trainer: Trainer
    pokemon: list[BattlePokemon] = field(init=False)  # Change to list
    active_index: int = 0

    def __post_init__(self):
        self.pokemon = [BattlePokemon(p) for p in self.trainer.pokemon]  # list, not set

    @property
    def active_pokemon(self):
        return self.pokemon[self.active_index]

    @property
    def reserve_pokemon(self):
        return [
            (i, p) for i, p in enumerate(self.pokemon)
            if i != self.active_index and p.pokemon.current_hp > 0
        ]

    @property
    def has_lost(self):
        return all(p.pokemon.current_hp <= 0 for p in self.pokemon)

    def switch(self, index: int):
        if index < 0 or index >= len(self.pokemon):
            raise ValueError("Invalid index")
        if self.pokemon[index].pokemon.current_hp <= 0:
            raise ValueError("Cannot switch to a fainted Pokemon")
        self.active_pokemon.switch_out()
        self.active_index = index
