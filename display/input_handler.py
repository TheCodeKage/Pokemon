from typing import Union
from models import BattleTrainer, Move


def get_input(trainer: BattleTrainer) -> Union[Move, int]:
    current = trainer.active_pokemon
    reserve = trainer.reserve_pokemon

    print(f"\n{trainer.trainer.name}'s {current.name} "
          f"(HP: {current.current_hp}/{current.pokemon.max_hp})")

    choice = int(input("\n  1. Fight\n  2. Switch\nEnter 1 or 2: "))

    if choice == 1:
        print("\nAvailable moves:")
        for i, move in enumerate(current.moves, 1):
            print(f"  {i}. {move.name} (PP: {move.current_pp}/{move.base_move.pp})")
        return current.moves[int(input("Enter 1-4: ")) - 1]
    else:
        print("\nAvailable Pokemon:")
        for i, (idx, p) in enumerate(reserve, 1):
            print(f"  {i}. {p.name} (HP: {p.current_hp}/{p.pokemon.max_hp})")
        switch_choice = int(input("Enter your choice: ")) - 1
        return reserve[switch_choice][0]

def get_forced_switch(trainer: BattleTrainer) -> int:
    """Prompts for a forced switch, returns the party index to switch to."""
    while True:
        print("\nAvailable Pokemon:")
        for i, (idx, p) in enumerate(trainer.reserve_pokemon, 1):
            print(f"  {i}. {p.name} (HP: {p.current_hp}/{p.pokemon.max_hp})")
        try:
            choice = int(input("Enter your choice: ")) - 1
            return trainer.reserve_pokemon[choice][0]
        except (ValueError, IndexError):
            print("Invalid choice, try again.")