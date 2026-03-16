from models import BattlePokemon, Weather, Type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.battle import BattleEngine


def apply_weather_damage(pkmn1: BattlePokemon, pkmn2: BattlePokemon, weather: Weather, log) -> None:
    match weather:
        case Weather.SAND:
            immune = {Type.GROUND, Type.ROCK, Type.STEEL}
            for pkmn in [pkmn1, pkmn2]:
                if not set(pkmn.pokemon.species.types) & immune:
                    damage = max(1, pkmn.pokemon.max_hp // 16)
                    pkmn.current_hp = max(0, pkmn.current_hp - damage)
                    log(f"{pkmn.name} was hit by the sandstorm!")
                    if pkmn.current_hp == 0:
                        log(f"{pkmn.name} fainted!")
        case Weather.HAIL:
            for pkmn in [pkmn1, pkmn2]:
                if Type.ICE not in pkmn.pokemon.species.types:
                    damage = max(1, pkmn.pokemon.max_hp // 16)
                    pkmn.current_hp = max(0, pkmn.current_hp - damage)
                    log(f"{pkmn.name} was hit by the hail!")
                    if pkmn.current_hp == 0:
                        log(f"{pkmn.name} fainted!")


def tick_weather(engine: "BattleEngine") -> None:
    """Decrements weather counter and clears weather on expiry. -1 = infinite."""
    if engine.weather_turns_remaining == -1:
        return
    if engine.weather_turns_remaining > 0:
        engine.weather_turns_remaining -= 1
        if engine.weather_turns_remaining == 0:
            engine.log("The weather cleared up!")
            engine.weather = Weather.CLEAR