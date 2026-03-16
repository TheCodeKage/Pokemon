from dataclasses import dataclass
from models import BattlePokemon, Move, Weather, Type, DamageClass
from engine.type_chart import get_effectiveness
import random


@dataclass
class DamageContext:
    attack: int
    defense: int
    level: int
    power: int
    stab: bool
    type_effectiveness: float
    weather_modifier: float


def build_damage_context(
    attacker: BattlePokemon,
    defender: BattlePokemon,
    move: Move,
    weather: Weather
) -> DamageContext:

    # attack and defense — your existing BattlePokemon properties
    # already handle stat stages and burn/paralysis
    if move.base_move.damage_class == DamageClass.PHYSICAL:
        attack = attacker.attack
        defense = defender.defense
    else:
        attack = attacker.special_attack
        defense = defender.special_defense
        # sand SpDef boost lives here, not in the formula
        if weather == Weather.SAND and Type.ROCK in defender.pokemon.species.types:
            defense = int(defense * 1.5)

    # weather move modifier resolved to a single float
    weather_modifier = _resolve_weather_modifier(move, weather)

    return DamageContext(
        attack=attack,
        defense=defense,
        level=attacker.pokemon.level,
        power=move.base_move.power or 0,
        stab=move.base_move.type in attacker.pokemon.species.types,
        type_effectiveness=get_effectiveness(
            move.base_move.type,
            defender.pokemon.species.types
        ),
        weather_modifier=weather_modifier,
    )


def _resolve_weather_modifier(move: Move, weather: Weather) -> float:
    match weather:
        case Weather.SUN:
            if move.base_move.type == Type.FIRE:
                return 1.5
            elif move.base_move.type == Type.WATER:
                return 0.5
        case Weather.RAIN:
            if move.base_move.type == Type.WATER:
                return 1.5
            elif move.base_move.type == Type.FIRE:
                return 0.5
    return 1.0


def calculate_damage(ctx: DamageContext) -> int:
    if ctx.power == 0:
        return 0
    damage = ((2 * ctx.level / 5 + 2) * ctx.power * ctx.attack / ctx.defense) / 50 + 2
    if ctx.stab:
        damage *= 1.5
    damage *= ctx.weather_modifier
    damage *= ctx.type_effectiveness
    damage *= random.uniform(0.85, 1.0)
    return int(damage)