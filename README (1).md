# Pokémon Battle Engine

A Python battle engine built on top of the [PokéAPI](https://pokeapi.co/), implementing core Gen 5+ battle mechanics including damage calculation, status conditions, weather effects, abilities, move priority, and move effects.

---

## Features

- **Damage formula** — Gen 5+ formula with STAB, type effectiveness, weather modifiers, and random factor
- **Type chart** — Full 18-type effectiveness matrix including dual-type multiplication
- **Status conditions** — Burn, Paralysis, Sleep, Freeze, Poison, Toxic with correct mechanics
- **Weather** — Sun, Rain, Sand, Hail with move modifiers, end-of-turn damage, and ability-set infinite weather
- **Ability hook system** — Event-driven hooks (`ON_SWITCH_IN`, `ON_BEFORE_MOVE`, `ON_AFTER_DAMAGE`, `ON_TURN_END`) with factory functions covering ~30 abilities
- **Move effects** — Status moves, stat boosts/drops, healing, recoil, drain, and secondary effects via a registry
- **Move priority & turn order** — Priority brackets, speed-based ordering, speed ties, and Trick Room
- **Forced switches** — Correct mid-turn and end-of-turn faint handling
- **PokéAPI integration** — Fetch real Pokémon, moves, and abilities by name
- **Disk caching** — JSON cache for all API responses to avoid redundant requests

---

## Project Structure

```
pokemon/
├── api/
│   ├── __init__.py
│   ├── request_manager.py   # Raw HTTP client + disk cache
│   └── wrapper.py           # Returns typed model objects
├── engine/
│   ├── __init__.py
│   ├── battle.py            # BattleEngine — orchestration only
│   ├── damage.py            # DamageContext, build_damage_context, calculate_damage
│   ├── status.py            # check_move_interrupt, apply_end_of_turn, try_apply_status
│   ├── weather.py           # apply_weather_damage, tick_weather
│   ├── abilities.py         # AbilityContext, factory functions, ABILITY_REGISTRY
│   ├── move_effects.py      # MoveContext, factory functions, MOVE_EFFECT_REGISTRY
│   ├── type_chart.py        # 18x18 effectiveness matrix
│   └── timer.py             # Async timer utility
├── models/
│   ├── __init__.py
│   ├── enums.py             # Type, DamageClass, StatusCondition, Weather, BattleHook, VolatileCondition
│   ├── move.py              # BaseMove, Move
│   ├── pokemon.py           # Stats, PokemonSpecies, Pokemon, BattlePokemon
│   ├── trainer.py           # Trainer, BattleTrainer
│   └── abilites.py          # Ability
├── display/
│   ├── __init__.py
│   ├── input_handler.py     # get_input, get_forced_switch
│   └── battle_simulator.py  # Example battle using real PokéAPI data
├── cache/                   # Auto-created JSON cache files
│   ├── pokemon.json
│   ├── moves.json
│   └── abilities.json
└── test_battle.py           # Full test suite
```

---

## Installation

```bash
pip install requests
```

No other dependencies. The cache directory is created automatically on first run.

---

## Quick Start

### Building a team from PokéAPI and starting a battle

```python
from api import PokeAPIClient
from engine import BattleEngine
from models import Pokemon, Trainer, Stats

client = PokeAPIClient()

# Fetch species data
charizard = client.get_pokemon("charizard")

# Fetch moves individually (only what you need)
flamethrower = client.get_move("flamethrower")
solar_beam   = client.get_move("solar-beam")
focus_blast  = client.get_move("focus-blast")
roost        = client.get_move("roost")

# Fetch ability
solar_power = client.get_ability("solar-power")

IVs = Stats(31, 31, 31, 31, 31, 31)
EVs = Stats(0, 0, 0, 252, 4, 252)

ch = Pokemon(charizard, [flamethrower, solar_beam, focus_blast, roost],
             IVs, EVs, solar_power, 100, "Charla")

ash  = Trainer("Ash",  1, [ch])
gary = Trainer("Gary", 2, [ch])   # same species, different instance

engine = BattleEngine(ash, gary)
engine.start_battle()
```

### Building manually without the API

```python
from models import *

tackle = BaseMove("Tackle", Type.NORMAL, 40, 100, 35, DamageClass.PHYSICAL)
no_ability = Ability("none", "no effect")

species = PokemonSpecies("TestMon", Stats(80,80,80,80,80,80),
                          [Type.NORMAL], [tackle], [no_ability])
pokemon = Pokemon(species, [tackle], Stats(31,31,31,31,31,31),
                  Stats(0,0,0,0,0,0), no_ability, 50)
```

---

## Architecture

### Separation of concerns

| Layer | Responsibility |
|---|---|
| `models/` | Pure data — no battle logic |
| `engine/damage.py` | Damage formula only — pure function, no engine reference |
| `engine/status.py` | All status condition logic |
| `engine/weather.py` | All weather logic |
| `engine/abilities.py` | Hook system + ability registry |
| `engine/move_effects.py` | Move effect registry |
| `engine/battle.py` | Orchestration only — sequences the above modules |
| `display/` | UI concerns — input handling |
| `api/` | Network layer — fetching and caching |

`BattleEngine` contains zero game logic directly. Adding a new mechanic means touching a specialist module, never `battle.py` itself.

### Event system

Abilities fire through named hooks at precise moments in the turn loop:

```
ON_SWITCH_IN      → Intimidate, Drizzle, Drought, Sand Stream, Snow Warning
ON_BEFORE_MOVE    → Lightning Rod, Levitate, Flash Fire, Storm Drain, Volt Absorb
ON_AFTER_DAMAGE   → Static, Flame Body, Poison Point
ON_TURN_END       → Speed Boost
```

### Adding a new ability

```python
# engine/abilities.py

# Using an existing factory:
ABILITY_REGISTRY["moxie"] = [(BattleHook.ON_AFTER_DAMAGE,
                               make_stat_modifier_on_switch('attack', +1, 'self',
                                                            "{name}'s Attack rose!"))]

# Or writing a custom handler:
def my_ability(ctx: AbilityContext):
    ctx.engine.log(f"{ctx.user.name} did something!")

ABILITY_REGISTRY["my-ability"] = [(BattleHook.ON_SWITCH_IN, my_ability)]
```

### Adding a new move effect

```python
# engine/move_effects.py

MOVE_EFFECT_REGISTRY["close-combat"] = [
    make_stat_effect('defense',          -1, target="attacker"),
    make_stat_effect('special_defense',  -1, target="attacker"),
]
```

---

## Damage Formula

```
damage = ((2 * level / 5 + 2) * power * attack / defense) / 50 + 2
       × STAB (1.5 if same type)
       × weather modifier
       × type effectiveness
       × random (0.85 – 1.0)
```

Sand boosts Rock-type Special Defense by 1.5× — resolved in `build_damage_context` before the formula runs.

---

## Status Conditions

| Condition | Effect | Type immunity |
|---|---|---|
| Burn | -1/16 max HP/turn, 50% Attack | Fire |
| Poison | -1/8 max HP/turn | Poison, Steel |
| Toxic | Escalating damage (n/16 max HP) | Poison, Steel |
| Paralysis | 25% skip chance, 50% Speed | — |
| Sleep | Can't move 1–3 turns | — |
| Freeze | Can't move, 20% thaw/turn, Fire moves thaw | Ice, cannot freeze in Sun |

---

## Weather Effects

| Weather | Move modifier | End-of-turn | SpDef boost |
|---|---|---|---|
| Sun | Fire ×1.5, Water ×0.5 | — | — |
| Rain | Water ×1.5, Fire ×0.5 | — | — |
| Sand | — | 1/16 max HP (non-Rock/Steel/Ground) | Rock types ×1.5 SpDef |
| Hail | — | 1/16 max HP (non-Ice) | — |

Weather set by abilities (Drizzle, Drought, Sand Stream, Snow Warning) lasts indefinitely. Weather set by moves lasts 5 turns.

---

## Running Tests

```bash
python test_battle.py
```

The test suite covers type chart accuracy, stat formula, stat stage multipliers, status condition immunities and mechanics, damage formula edge cases, weather damage and modifiers, ability hook firing, turn order and priority, BattlePokemon state management, trainer validation, and BattleEngine integration.

---

## Caching

API responses are cached to `cache/pokemon.json`, `cache/moves.json`, and `cache/abilities.json`. The cache is loaded on startup and saved every 10 new requests, and again on exit via `atexit`. On a warm cache, startup is near-instant with no network requests.

To clear the cache and re-fetch everything, delete the files in `cache/`.

---

## Limitations & Known Gaps

- **No move effects for some categories** — Protect, Substitute, multi-hit moves, and variable-power moves (Electro Ball, Gyro Ball) are not implemented
- **No held items** — no items system exists yet
- **No critical hits** — the damage formula does not include the critical hit roll
- **No PP-out handling** — using a move with 0 PP raises an exception rather than using Struggle
- **Single battle format only** — double/triple battles are not supported
- **No network error handling** — API failures raise exceptions rather than retrying
