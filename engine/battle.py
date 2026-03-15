from engine.type_chart import get_effectiveness
from models import Trainer, Move, BattlePokemon, BattleTrainer, DamageClass
from dataclasses import dataclass, field, InitVar
from typing import Union, Tuple
import random


def get_input(trainer: BattleTrainer) -> Union[Move, int]:
    """Get player input for battle action. Returns Move or switch index."""
    current_pokemon = trainer.active_pokemon
    reserve_pokemon = trainer.reserve_pokemon

    print(f"\n{trainer.trainer.name}'s {current_pokemon.name} (HP: {current_pokemon.pokemon.current_hp}/{current_pokemon.pokemon.max_hp})")

    choice = int(input("""
    What do you choose?
        1. Fight
        2. Switch Pokemon
    Enter 1 or 2: """))

    if choice == 1:
        moves = current_pokemon.moves
        print("\nAvailable moves:")
        for i, move in enumerate(moves, 1):
            print(f"  {i}. {move.name} (PP: {move.current_pp}/{move.base_move.pp})")
        move_choice = int(input("Enter 1, 2, 3 or 4: ")) - 1
        return moves[move_choice]
    else:
        print("\nAvailable Pokemon:")
        for i, (idx, p) in enumerate(reserve_pokemon, 1):
            print(f"  {i}. {p.name} (HP: {p.pokemon.current_hp}/{p.pokemon.max_hp})")
        switch_choice = int(input("Enter your choice: ")) - 1
        return reserve_pokemon[switch_choice][0]  # Return the index


@dataclass
class BattleEngine:
    trainer1_data: InitVar[Trainer]
    trainer2_data: InitVar[Trainer]
    trainer1: BattleTrainer = field(init=False)
    trainer2: BattleTrainer = field(init=False)
    turn: int = field(init=False, default=0)
    weather: str = field(init=False, default="")
    battle_log: list[str] = field(init=False, default_factory=list)

    def __post_init__(self, trainer1_data: Trainer, trainer2_data: Trainer):
        self.trainer1 = BattleTrainer(trainer1_data)
        self.trainer2 = BattleTrainer(trainer2_data)

    def log(self, message: str):
        """Add message to battle log and print it"""
        self.battle_log.append(message)
        print(message)

    def calculate_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move: Move) -> int:
        """Calculate damage using Pokemon damage formula"""
        if move.base_move.damage_class == DamageClass.STATUS:
            return 0

        # Determine attack and defense stats
        if move.base_move.damage_class == DamageClass.PHYSICAL:
            attack = attacker.attack
            defense = defender.defense
        else:  # SPECIAL
            attack = attacker.special_attack
            defense = defender.special_defense

        # Base damage calculation
        level = attacker.pokemon.level
        power = move.base_move.power
        damage = ((2 * level / 5 + 2) * power * attack / defense) / 50 + 2

        # STAB (Same Type Attack Bonus)
        if move.base_move.type in attacker.pokemon.species.types:
            damage *= 1.5

        # Type effectiveness (simplified - you'd need a type chart)
        damage *= get_effectiveness(move.base_move.type, defender.pokemon.species.types)

        # Random factor (0.85 to 1.0)
        damage *= random.uniform(0.85, 1.0)

        return int(damage)

    def execute_move(self, attacker_trainer: BattleTrainer, defender_trainer: BattleTrainer, move: Move):
        """Execute a move from attacker to defender"""
        attacker = attacker_trainer.active_pokemon
        defender = defender_trainer.active_pokemon

        self.log(f"{attacker.name} used {move.name}!")

        # Check accuracy
        if move.base_move.accuracy is not None and random.randint(1, 100) > move.base_move.accuracy:
            self.log("The attack missed!")
            return

        # Use the move
        move.use()

        # Calculate and apply damage
        damage = self.calculate_damage(attacker, defender, move)
        if damage > 0:
            defender.pokemon.current_hp = max(0, defender.pokemon.current_hp - damage)
            self.log(f"{defender.name} took {damage} damage! (HP: {defender.pokemon.current_hp}/{defender.pokemon.max_hp})")

            if defender.pokemon.current_hp == 0:
                self.log(f"{defender.name} fainted!")

    def determine_turn_order(self, action1: Union[Move, int], action2: Union[Move, int]) -> list[Tuple[BattleTrainer, Union[Move, int]]]:
        """Determine which action goes first. Switches always go first."""
        # Both switch
        if isinstance(action1, int) and isinstance(action2, int):
            return [(self.trainer1, action1), (self.trainer2, action2)]

        # Trainer1 switches
        if isinstance(action1, int):
            return [(self.trainer1, action1), (self.trainer2, action2)]

        # Trainer2 switches
        if isinstance(action2, int):
            return [(self.trainer2, action2), (self.trainer1, action1)]

        # Both attack - compare speed
        if self.trainer1.active_pokemon.speed >= self.trainer2.active_pokemon.speed:
            return [(self.trainer1, action1), (self.trainer2, action2)]
        else:
            return [(self.trainer2, action2), (self.trainer1, action1)]

    def execute_turn(self, action1: Union[Move, int], action2: Union[Move, int]):
        """Execute a single turn of battle"""
        turn_order = self.determine_turn_order(action1, action2)

        for trainer, action in turn_order:
            opponent = self.trainer2 if trainer == self.trainer1 else self.trainer1

            # Check if trainer's pokemon has fainted
            if trainer.active_pokemon.pokemon.current_hp == 0:
                continue

            # Execute action
            if isinstance(action, int):
                # Switch
                old_name = trainer.active_pokemon.name
                trainer.switch(action)
                self.log(f"{trainer.trainer.name} switched to {trainer.active_pokemon.name}!")
            else:
                # Attack
                self.execute_move(trainer, opponent, action)

                # Check if opponent fainted
                if opponent.active_pokemon.pokemon.current_hp == 0:
                    # Force switch if they have pokemon left
                    if not opponent.has_lost and len(opponent.reserve_pokemon) > 0:
                        self.log(f"{opponent.trainer.name} must switch Pokemon!")
                        # In a real game, you'd handle forced switches here

    def start_battle(self):
        """Main battle loop"""
        self.log(f"Battle start! {self.trainer1.trainer.name} vs {self.trainer2.trainer.name}!")
        self.log(f"{self.trainer1.trainer.name} sent out {self.trainer1.active_pokemon.name}!")
        self.log(f"{self.trainer2.trainer.name} sent out {self.trainer2.active_pokemon.name}!")

        while not self.trainer1.has_lost and not self.trainer2.has_lost:
            self.turn += 1
            self.log(f"\n--- Turn {self.turn} ---")

            # Get actions from both trainers
            action1 = get_input(self.trainer1)
            action2 = get_input(self.trainer2)

            # Execute turn
            self.execute_turn(action1, action2)

        # Battle end
        if self.trainer1.has_lost:
            self.log(f"\n{self.trainer2.trainer.name} won the battle!")
        else:
            self.log(f"\n{self.trainer1.trainer.name} won the battle!")


