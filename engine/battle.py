from engine.abilities import ABILITY_REGISTRY, AbilityContext
from engine.damage import build_damage_context, calculate_damage
from engine import status, weather as weather_module
from models import (Trainer, Move, BattlePokemon, BattleTrainer,
                    StatusCondition, Type, Weather, BattleHook)
from dataclasses import dataclass, field, InitVar
from typing import Union, Tuple
import random
from display.input_handler import get_input


@dataclass
class BattleEngine:
    trainer1_data: InitVar[Trainer]
    trainer2_data: InitVar[Trainer]
    trainer1: BattleTrainer = field(init=False)
    trainer2: BattleTrainer = field(init=False)
    turn: int = field(init=False, default=0)
    weather: Weather = field(init=False, default=Weather.CLEAR)
    weather_turns_remaining: int = field(init=False, default=0)
    battle_log: list[str] = field(init=False, default_factory=list)
    trick_room_active: bool = field(init=False, default=False)

    def __post_init__(self, trainer1_data: Trainer, trainer2_data: Trainer):
        self.trainer1 = BattleTrainer(trainer1_data)
        self.trainer2 = BattleTrainer(trainer2_data)

    def log(self, message: str):
        self.battle_log.append(message)
        print(message)

    def fire_hook(self, hook: BattleHook, user: BattlePokemon,
                  user_trainer: BattleTrainer, opponent=None, **kwargs) -> AbilityContext:
        ability_name = user.pokemon.ability.name.lower()
        ctx = AbilityContext(engine=self, user=user, user_trainer=user_trainer,
                             opponent=opponent, **kwargs)
        for registered_hook, fn in ABILITY_REGISTRY.get(ability_name, []):
            if registered_hook == hook:
                fn(ctx)
        return ctx

    def set_weather(self, new_weather: Weather, turns: int = 5):
        self.weather = new_weather
        self.weather_turns_remaining = turns
        match new_weather:
            case Weather.SUN:  self.log("The sunlight turned harsh!")
            case Weather.RAIN: self.log("It started to rain!")
            case Weather.SAND: self.log("A sandstorm kicked up!")
            case Weather.HAIL: self.log("It started to hail!")

    def get_effective_speed(self, bp: BattlePokemon) -> int:
        speed = bp.speed
        ability = bp.pokemon.ability.name.lower()
        if ability == "swift-swim" and self.weather == Weather.RAIN:
            speed *= 2
        elif ability == "chlorophyll" and self.weather == Weather.SUN:
            speed *= 2
        elif ability == "sand-rush" and self.weather == Weather.SAND:
            speed *= 2
        return speed if not self.trick_room_active else -speed

    def determine_turn_order(self, action1: Union[Move, int],
                             action2: Union[Move, int]) -> list[Tuple[BattleTrainer, Union[Move, int]]]:
        actions = [
            (self.trainer1, action1),
            (self.trainer2, action2),
        ]
        actions.sort(key=lambda x: self._action_priority(x[0], x[1]), reverse=True)
        return actions

    def _action_priority(self, trainer: BattleTrainer, action: Union[Move, int]) -> tuple:
        """
        Returns a sort key (higher = goes first).
        Switches always beat moves, so they get priority bracket 7.
        Within moves, sort by: priority bracket, then effective speed.
        Speed ties are broken randomly.
        """
        if isinstance(action, int):
            return 7, 0, 0  # switches always go first
        move_priority = action.base_move.priority
        speed = self.get_effective_speed(trainer.active_pokemon)
        tiebreak = random.random()  # random for speed ties
        return move_priority, speed, tiebreak

    def execute_move(self, attacker_trainer: BattleTrainer,
                     defender_trainer: BattleTrainer, move: Move):
        attacker = attacker_trainer.active_pokemon
        defender = defender_trainer.active_pokemon

        # Status interrupt check — delegated to status module
        if status.check_move_interrupt(attacker, self.log):
            return

        self.log(f"{attacker.name} used {move.name}!")

        # Ability hook — defender's ability may cancel the move
        ctx = self.fire_hook(BattleHook.ON_BEFORE_MOVE, defender, defender_trainer,
                             opponent=attacker, move_type=move.base_move.type)
        if ctx.cancelled:
            return

        if move.base_move.accuracy is not None and \
                random.randint(1, 100) > move.base_move.accuracy:
            self.log("The attack missed!")
            return

        move.use()

        damage_ctx = build_damage_context(attacker, defender, move, self.weather)
        damage = calculate_damage(damage_ctx)

        if damage > 0:
            defender.current_hp = max(0, defender.current_hp - damage)
            self.log(f"{defender.name} took {damage} damage! "
                     f"(HP: {defender.current_hp}/{defender.pokemon.max_hp})")

            # Fire-thaw
            if (defender.status_condition == StatusCondition.FREEZE
                    and move.base_move.type == Type.FIRE):
                defender.status_condition = None
                self.log(f"{defender.name} was defrosted!")

            if defender.current_hp == 0:
                self.log(f"{defender.name} fainted!")

    def _handle_faint(self, trainer: BattleTrainer):
        """Prompt forced switch after a faint. Stub for now."""
        if not trainer.has_lost and len(trainer.reserve_pokemon) > 0:
            self.log(f"{trainer.trainer.name} must switch Pokemon!")

    def _end_of_turn(self):
        """All end-of-turn effects in correct order."""
        for trainer in [self.trainer1, self.trainer2]:
            pkmn = trainer.active_pokemon
            status.apply_end_of_turn(pkmn, self.log)
            if pkmn.current_hp == 0:
                self._handle_faint(trainer)

        weather_module.apply_weather_damage(
            self.trainer1.active_pokemon,
            self.trainer2.active_pokemon,
            self.weather, self.log
        )
        for trainer in [self.trainer1, self.trainer2]:
            if trainer.active_pokemon.current_hp == 0:
                self._handle_faint(trainer)

        weather_module.tick_weather(self)

    def execute_turn(self, action1: Union[Move, int], action2: Union[Move, int]):
        for trainer, action in self.determine_turn_order(action1, action2):
            opponent = self.trainer2 if trainer == self.trainer1 else self.trainer1
            if trainer.active_pokemon.current_hp == 0:
                continue
            if isinstance(action, int):
                trainer.switch(action)
                self.log(f"{trainer.trainer.name} switched to {trainer.active_pokemon.name}!")
                self.fire_hook(BattleHook.ON_SWITCH_IN, trainer.active_pokemon,
                               trainer, opponent=opponent.active_pokemon)
            else:
                self.execute_move(trainer, opponent, action)
                if opponent.active_pokemon.current_hp == 0:
                    self._handle_faint(opponent)

        self._end_of_turn()

    def start_battle(self):
        self.log(f"Battle start! {self.trainer1.trainer.name} vs {self.trainer2.trainer.name}!")
        self.log(f"{self.trainer1.trainer.name} sent out {self.trainer1.active_pokemon.name}!")
        self.log(f"{self.trainer2.trainer.name} sent out {self.trainer2.active_pokemon.name}!")

        self.fire_hook(BattleHook.ON_SWITCH_IN, self.trainer1.active_pokemon,
                       self.trainer1, opponent=self.trainer2.active_pokemon)
        self.fire_hook(BattleHook.ON_SWITCH_IN, self.trainer2.active_pokemon,
                       self.trainer2, opponent=self.trainer1.active_pokemon)

        while not self.trainer1.has_lost and not self.trainer2.has_lost:
            self.turn += 1
            self.log(f"\n--- Turn {self.turn} ---")
            action1 = get_input(self.trainer1)
            action2 = get_input(self.trainer2)
            self.execute_turn(action1, action2)

        if self.trainer1.has_lost:
            self.log(f"\n{self.trainer2.trainer.name} won the battle!")
        else:
            self.log(f"\n{self.trainer1.trainer.name} won the battle!")