import random

from models import BattlePokemon, StatusCondition, Type, Weather


def check_move_interrupt(pokemon: BattlePokemon, log) -> bool:
    """Returns True if the pokemon cannot move this turn."""
    if pokemon.status_condition == StatusCondition.SLEEP:
        if pokemon.sleep_counter > 0:
            pokemon.sleep_counter -= 1
            log(f"{pokemon.name} is fast asleep!")
            return True
        else:
            pokemon.status_condition = None
            log(f"{pokemon.name} woke up!")
            return False

    if pokemon.status_condition == StatusCondition.FREEZE:
        if random.randint(1, 100) <= 20:
            pokemon.status_condition = None
            log(f"{pokemon.name} thawed out!")
            return False
        else:
            log(f"{pokemon.name} is frozen solid!")
            return True

    if pokemon.status_condition == StatusCondition.PARALYSIS:
        if random.randint(1, 100) <= 25:
            log(f"{pokemon.name} is fully paralyzed and can't move!")
            return True

    return False


def apply_end_of_turn(pokemon: BattlePokemon, log) -> None:
    """Applies burn/poison/toxic chip damage at end of turn."""
    if pokemon.status_condition is None:
        return

    match pokemon.status_condition:
        case StatusCondition.BURN:
            damage = max(1, pokemon.pokemon.max_hp // 16)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            log(f"{pokemon.name} is hurt by its burn!")
        case StatusCondition.POISON:
            damage = max(1, pokemon.pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            log(f"{pokemon.name} is hurt by poison!")
        case StatusCondition.TOXIC:
            pokemon.toxic_counter += 1
            damage = max(1, pokemon.pokemon.max_hp * pokemon.toxic_counter // 16)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            log(f"{pokemon.name} is hurt by poison! ({damage} damage)")
        case _:
            pass

    if pokemon.current_hp == 0:
        log(f"{pokemon.name} fainted!")


def try_apply_status(pokemon: BattlePokemon, condition: StatusCondition, weather: Weather = None) -> bool:
    """
    Applies a status condition if the pokemon isn't immune.
    Returns True if successfully applied.
    """
    if pokemon.status_condition is not None:
        return False
    if condition == StatusCondition.FREEZE:
        if Type.ICE in pokemon.pokemon.species.types:
            return False
        if weather == Weather.SUN:
            return False
    if condition == StatusCondition.BURN and Type.FIRE in pokemon.pokemon.species.types:
        return False
    if condition == StatusCondition.POISON and (
        Type.POISON in pokemon.pokemon.species.types
        or Type.STEEL in pokemon.pokemon.species.types
    ):
        return False

    pokemon.status_condition = condition
    if condition == StatusCondition.SLEEP:
        pokemon.sleep_counter = random.randint(1, 3)
    return True