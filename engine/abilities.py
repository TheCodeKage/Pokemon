from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from engine.battle import BattleEngine
    from models import BattlePokemon, BattleTrainer, Stats


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


from models import StatusCondition, Type, Weather


def intimidate(ctx: AbilityContext):
    if ctx.opponent is None:
        return
    changed = modify_stat(ctx.opponent, 'attack', -1)
    if changed:
        ctx.engine.log(f"{ctx.opponent.name}'s Attack fell!")


def drizzle(ctx: AbilityContext):
    ctx.engine.set_weather(Weather.RAIN, turns=-1)


def drought(ctx: AbilityContext):
    ctx.engine.set_weather(Weather.SUN, turns=-1)


def sand_stream(ctx: AbilityContext):
    ctx.engine.set_weather(Weather.SAND, turns=-1)


def snow_warning(ctx: AbilityContext):
    ctx.engine.set_weather(Weather.HAIL, turns=-1)


def swift_swim(ctx: AbilityContext):
    # Doubles speed in rain — handled in BattlePokemon.speed via context
    pass  # see note below


def lightning_rod(ctx: AbilityContext):
    if ctx.move_type == Type.ELECTRIC:
        ctx.cancelled = True
        ctx.engine.log(f"{ctx.user.name} absorbed the electric attack!")


def flash_fire(ctx: AbilityContext):
    if ctx.move_type == Type.FIRE:
        ctx.cancelled = True
        ctx.user.flash_fire_active = True
        ctx.engine.log(f"{ctx.user.name}'s Flash Fire was activated!")


def levitate(ctx: AbilityContext):
    if ctx.move_type == Type.GROUND:
        ctx.cancelled = True
        ctx.engine.log(f"{ctx.user.name} is unaffected due to Levitate!")


from models.enums import BattleHook


ABILITY_REGISTRY: dict[str, list[tuple[BattleHook, Callable]]] = {
    "intimidate":   [(BattleHook.ON_SWITCH_IN, intimidate)],
    "drizzle":      [(BattleHook.ON_SWITCH_IN, drizzle)],
    "drought":      [(BattleHook.ON_SWITCH_IN, drought)],
    "sand-stream":  [(BattleHook.ON_SWITCH_IN, sand_stream)],
    "snow-warning": [(BattleHook.ON_SWITCH_IN, snow_warning)],
    "lightning-rod":[(BattleHook.ON_BEFORE_MOVE, lightning_rod)],
    "flash-fire":   [(BattleHook.ON_BEFORE_MOVE, flash_fire)],
    "levitate":     [(BattleHook.ON_BEFORE_MOVE, levitate)],
    "swift-swim":   [],  # handled differently — see speed note below
}
