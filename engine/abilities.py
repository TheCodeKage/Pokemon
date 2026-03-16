import random
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Optional, Callable
from models import StatusCondition, Type, Weather, BattleHook, Stats

if TYPE_CHECKING:
    from engine.battle import BattleEngine
    from models import BattlePokemon, BattleTrainer


@dataclass
class AbilityContext:
    engine: "BattleEngine"
    user: "BattlePokemon"  # the pokemon with the ability
    user_trainer: "BattleTrainer"
    opponent: Optional["BattlePokemon"] = None
    move_type: Optional[object] = None  # Type enum
    damage: Optional[int] = None  # mutable — abilities can modify this
    cancelled: bool = False  # set True to block an effect

def modify_stat(bp, stat_name: str, delta: int):
    current = getattr(bp.stat_changes, stat_name)
    new_val = max(-6, min(6, current + delta))
    kwargs = {f.name: getattr(bp.stat_changes, f.name) for f in fields(bp.stat_changes)}
    kwargs[stat_name] = new_val
    bp.stat_changes = Stats(**kwargs)
    return new_val != current

def make_type_immunity(
    immune_type: Type,
    heal: bool = False,
    boost_stat: str = None,
    boost_delta: int = 1,
    message: str = None
):
    """
    Cancels moves of immune_type hitting the user.
    Optionally heals 1/4 max HP, or boosts a stat.
    """
    def handler(ctx: AbilityContext):
        if ctx.move_type != immune_type:
            return
        ctx.cancelled = True
        msg = (message or f"{ctx.user.name} is unaffected!").format(name=ctx.user.name)
        ctx.engine.log(msg)
        if heal:
            amount = ctx.user.pokemon.max_hp // 4
            ctx.user.current_hp = min(ctx.user.pokemon.max_hp,
                                      ctx.user.current_hp + amount)
            ctx.engine.log(f"{ctx.user.name} restored some HP!")
        if boost_stat:
            changed = modify_stat(ctx.user, boost_stat, boost_delta)
            if changed:
                ctx.engine.log(f"{ctx.user.name}'s {boost_stat} rose!")
    return handler

def make_weather_setter(weather: Weather):
    def handler(ctx: AbilityContext):
        ctx.engine.set_weather(weather, turns=-1)
    return handler

def make_contact_status(
    condition: StatusCondition,
    chance: int,
    message: str = None
):
    """
    On contact (ON_AFTER_DAMAGE hook), applies condition to attacker
    with given chance (0-100).
    """
    def handler(ctx: AbilityContext):
        if ctx.opponent is None:
            return
        if random.randint(1, 100) > chance:
            return
        from engine.status import try_apply_status
        applied = try_apply_status(ctx.opponent, condition,
                                   weather=ctx.engine.weather)
        if applied:
            msg = message or f"{ctx.opponent.name} was inflicted with {condition.value}!"
            ctx.engine.log(msg)
    return handler

def make_stat_modifier_on_switch(
    stat: str,
    delta: int,
    target: str = "opponent",   # "opponent" or "self"
    message: str = None
):
    def handler(ctx: AbilityContext):
        bp = ctx.opponent if target == "opponent" else ctx.user
        if bp is None:
            return
        changed = modify_stat(bp, stat, delta)
        if changed and message:
            ctx.engine.log(message.format(name=bp.name))
    return handler

def make_damage_modifier(
    condition_fn,   # callable(ctx) -> bool
    multiplier: float
):
    def handler(ctx: AbilityContext):
        if condition_fn(ctx):
            ctx.damage = int((ctx.damage or 1) * multiplier)
    return handler

# Usage examples:
adaptability = make_damage_modifier(
    condition_fn=lambda ctx: ctx.move_type in ctx.user.pokemon.species.types,
    multiplier=1.333   # turns 1.5x STAB into 2x effectively
)

def make_end_of_turn_effect(fn):
    """Wraps any callable as an ON_TURN_END handler."""
    def handler(ctx: AbilityContext):
        fn(ctx)
    return handler

# Example — Speed Boost
def _speed_boost(ctx: AbilityContext):
    changed = modify_stat(ctx.user, 'speed', 1)
    if changed:
        ctx.engine.log(f"{ctx.user.name}'s Speed rose!")

speed_boost = make_end_of_turn_effect(_speed_boost)

ABILITY_REGISTRY: dict[str, list[tuple[BattleHook, Callable]]] = {
    # weather setters
    "drizzle":       [(BattleHook.ON_SWITCH_IN, make_weather_setter(Weather.RAIN))],
    "drought":       [(BattleHook.ON_SWITCH_IN, make_weather_setter(Weather.SUN))],
    "sand-stream":   [(BattleHook.ON_SWITCH_IN, make_weather_setter(Weather.SAND))],
    "snow-warning":  [(BattleHook.ON_SWITCH_IN, make_weather_setter(Weather.HAIL))],

    # stat modifiers on switch-in
    "intimidate":    [(BattleHook.ON_SWITCH_IN,
                       make_stat_modifier_on_switch('attack', -1, 'opponent',
                                                    "{name}'s Attack fell!"))],

    # type immunities — cancel only
    "levitate":      [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.GROUND,
                                          message="{name} is unaffected due to Levitate!"))],
    "lightning-rod": [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.ELECTRIC, boost_stat='special_attack',
                                          message="{name} absorbed the electric attack!"))],
    "storm-drain":   [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.WATER, boost_stat='special_attack',
                                          message="{name} absorbed the water attack!"))],
    "flash-fire":    [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.FIRE,
                                          message="{name}'s Flash Fire was activated!"))],
    "sap-sipper":    [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.GRASS, boost_stat='attack',
                                          message="{name}'s Attack rose!"))],

    # type immunities — heal
    "volt-absorb":   [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.ELECTRIC, heal=True,
                                          message="{name} absorbed the electric attack!"))],
    "water-absorb":  [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.WATER, heal=True,
                                          message="{name} absorbed the water attack!"))],
    "motor-drive":   [(BattleHook.ON_BEFORE_MOVE,
                       make_type_immunity(Type.ELECTRIC, boost_stat='speed',
                                          message="{name}'s Speed rose!"))],

    # contact status
    "static":        [(BattleHook.ON_AFTER_DAMAGE,
                       make_contact_status(StatusCondition.PARALYSIS, 30,
                                           "{name} was paralyzed!"))],
    "flame-body":    [(BattleHook.ON_AFTER_DAMAGE,
                       make_contact_status(StatusCondition.BURN, 30,
                                           "{name} was burned!"))],
    "poison-point":  [(BattleHook.ON_AFTER_DAMAGE,
                       make_contact_status(StatusCondition.POISON, 30,
                                           "{name} was poisoned!"))],

    # speed weather abilities — handled in get_effective_speed
    "swift-swim":    [],
    "chlorophyll":   [],
    "sand-rush":     [],

    # end-of-turn
    "speed-boost":   [(BattleHook.ON_TURN_END, speed_boost)],
}