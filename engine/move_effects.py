# engine/move_effects.py
import random
from typing import TYPE_CHECKING, Optional, Callable
from dataclasses import dataclass
from models import BattlePokemon, StatusCondition, Weather, Stats
from engine.status import try_apply_status
from engine.abilities import modify_stat

if TYPE_CHECKING:
    from engine.battle import BattleEngine
    from models import BattleTrainer


@dataclass
class MoveContext:
    engine: "BattleEngine"
    attacker: BattlePokemon
    defender: BattlePokemon
    attacker_trainer: "BattleTrainer"
    defender_trainer: "BattleTrainer"
    damage_dealt: int        # 0 for status moves
    move_hit: bool           # False if move missed


def make_status_effect(
    condition: StatusCondition,
    chance: int = 100,       # 100 = always (status moves), <100 = secondary effect
    target: str = "defender" # "defender" or "attacker"
):
    def handler(ctx: MoveContext):
        if not ctx.move_hit:
            return
        if random.randint(1, 100) > chance:
            return
        bp = ctx.defender if target == "defender" else ctx.attacker
        applied = try_apply_status(bp, condition, weather=ctx.engine.weather)
        if applied:
            match condition:
                case StatusCondition.PARALYSIS:
                    ctx.engine.log(f"{bp.name} is paralyzed!")
                case StatusCondition.BURN:
                    ctx.engine.log(f"{bp.name} was burned!")
                case StatusCondition.POISON:
                    ctx.engine.log(f"{bp.name} was poisoned!")
                case StatusCondition.TOXIC:
                    ctx.engine.log(f"{bp.name} was badly poisoned!")
                case StatusCondition.SLEEP:
                    ctx.engine.log(f"{bp.name} fell asleep!")
                case StatusCondition.FREEZE:
                    ctx.engine.log(f"{bp.name} was frozen solid!")
    return handler

def make_stat_effect(
    stat: str,
    stages: int,
    target: str = "attacker",  # "attacker" or "defender"
    chance: int = 100
):
    stat_names = {
        'attack': 'Attack', 'defense': 'Defense',
        'special_attack': 'Sp. Atk', 'special_defense': 'Sp. Def',
        'speed': 'Speed'
    }
    def handler(ctx: MoveContext):
        if not ctx.move_hit:
            return
        if random.randint(1, 100) > chance:
            return
        bp = ctx.attacker if target == "attacker" else ctx.defender
        changed = modify_stat(bp, stat, stages)
        if changed:
            direction = "rose" if stages > 0 else "fell"
            sharply = abs(stages) >= 2
            adverb = " sharply" if sharply else ""
            ctx.engine.log(f"{bp.name}'s {stat_names.get(stat, stat)}{adverb} {direction}!")
        else:
            limit = "higher" if stages > 0 else "lower"
            ctx.engine.log(f"{bp.name}'s {stat_names.get(stat, stat)} won't go any {limit}!")
    return handler

def make_heal_effect(fraction: float = 0.5):
    def handler(ctx: MoveContext):
        if not ctx.move_hit:
            return
        bp = ctx.attacker
        amount = int(bp.pokemon.max_hp * fraction)
        bp.current_hp = min(bp.pokemon.max_hp, bp.current_hp + amount)
        ctx.engine.log(f"{bp.name} restored HP!")
    return handler

def make_recoil_effect(fraction: float):
    """Attacker takes fraction of damage dealt as recoil."""
    def handler(ctx: MoveContext):
        if ctx.damage_dealt <= 0:
            return
        recoil = max(1, int(ctx.damage_dealt * fraction))
        ctx.attacker.current_hp = max(0, ctx.attacker.current_hp - recoil)
        ctx.engine.log(f"{ctx.attacker.name} is hurt by recoil!")
        if ctx.attacker.current_hp == 0:
            ctx.engine.log(f"{ctx.attacker.name} fainted!")
    return handler

def make_drain_effect(fraction: float = 0.5):
    """Attacker heals fraction of damage dealt."""
    def handler(ctx: MoveContext):
        if ctx.damage_dealt <= 0:
            return
        heal = max(1, int(ctx.damage_dealt * fraction))
        ctx.attacker.current_hp = min(ctx.attacker.pokemon.max_hp,
                                       ctx.attacker.current_hp + heal)
        ctx.engine.log(f"{ctx.attacker.name} drained energy!")
    return handler


MOVE_EFFECT_REGISTRY: dict[str, Callable] = {
    # status moves — always apply
    "thunder-wave":   make_status_effect(StatusCondition.PARALYSIS),
    "glare":          make_status_effect(StatusCondition.PARALYSIS),
    "stun-spore":     make_status_effect(StatusCondition.PARALYSIS),
    "toxic":          make_status_effect(StatusCondition.TOXIC),
    "poison-powder":  make_status_effect(StatusCondition.POISON),
    "will-o-wisp":    make_status_effect(StatusCondition.BURN),
    "spore":          make_status_effect(StatusCondition.SLEEP),
    "sleep-powder":   make_status_effect(StatusCondition.SLEEP),
    "hypnosis":       make_status_effect(StatusCondition.SLEEP),

    # secondary status effects — chance-based
    "thunderbolt":    make_status_effect(StatusCondition.PARALYSIS, chance=10),
    "thunder":        make_status_effect(StatusCondition.PARALYSIS, chance=30),
    "flamethrower":   make_status_effect(StatusCondition.BURN,      chance=10),
    "fire-blast":     make_status_effect(StatusCondition.BURN,      chance=10),
    "ember":          make_status_effect(StatusCondition.BURN,      chance=10),
    "ice-beam":       make_status_effect(StatusCondition.FREEZE,    chance=10),
    "blizzard":       make_status_effect(StatusCondition.FREEZE,    chance=10),
    "body-slam":      make_status_effect(StatusCondition.PARALYSIS, chance=30),
    "poison-jab":     make_status_effect(StatusCondition.POISON,    chance=30),
    "sludge-bomb":    make_status_effect(StatusCondition.POISON,    chance=30),

    # self stat boosts
    "swords-dance":   make_stat_effect('attack',          +2),
    "nasty-plot":     make_stat_effect('special_attack',  +2),
    "calm-mind":      [make_stat_effect('special_attack', +1),
                       make_stat_effect('special_defense',+1)],
    "dragon-dance":   [make_stat_effect('attack',         +1),
                       make_stat_effect('speed',          +1)],
    "bulk-up":        [make_stat_effect('attack',         +1),
                       make_stat_effect('defense',        +1)],
    "agility":        make_stat_effect('speed',           +2),
    "iron-defense":   make_stat_effect('defense',         +2),
    "amnesia":        make_stat_effect('special_defense', +2),

    # opponent stat drops
    "growl":          make_stat_effect('attack',          -1, target="defender"),
    "leer":           make_stat_effect('defense',         -1, target="defender"),
    "screech":        make_stat_effect('defense',         -2, target="defender"),
    "tail-whip":      make_stat_effect('defense',         -1, target="defender"),
    "string-shot":    make_stat_effect('speed',           -1, target="defender"),

    # secondary stat drops
    "crunch":         make_stat_effect('defense',         -1, target="defender", chance=20),
    "psychic":        make_stat_effect('special_defense', -1, target="defender", chance=10),
    "energy-ball":    make_stat_effect('special_defense', -1, target="defender", chance=10),

    # healing
    "recover":        make_heal_effect(0.5),
    "roost":          make_heal_effect(0.5),
    "moonlight":      make_heal_effect(0.5),
    "synthesis":      make_heal_effect(0.5),
    "slack-off":      make_heal_effect(0.5),
    "soft-boiled":    make_heal_effect(0.5),
    "rest":           make_heal_effect(1.0),   # heals fully, sleep handled separately

    # recoil
    "volt-tackle":    make_recoil_effect(1/3),
    "flare-blitz":    make_recoil_effect(1/3),
    "brave-bird":     make_recoil_effect(1/3),
    "double-edge":    make_recoil_effect(1/3),
    "take-down":      make_recoil_effect(0.25),
    "head-smash":     make_recoil_effect(0.5),

    # drain
    "absorb":         make_drain_effect(0.5),
    "mega-drain":     make_drain_effect(0.5),
    "giga-drain":     make_drain_effect(0.5),
    "leech-life":     make_drain_effect(0.5),
    "drain-punch":    make_drain_effect(0.5),
}