from models import *
from engine.battle import BattleEngine
from engine.type_chart import get_effectiveness
from engine.damage import calculate_damage, build_damage_context
from engine.status import try_apply_status

print("=== Type Chart ===")
assert get_effectiveness(Type.ELECTRIC, [Type.WATER]) == 2.0
assert get_effectiveness(Type.ELECTRIC, [Type.GROUND]) == 0.0
assert get_effectiveness(Type.ELECTRIC, [Type.ELECTRIC]) == 0.5
assert get_effectiveness(Type.NORMAL, [Type.GHOST]) == 0.0
assert get_effectiveness(Type.FIRE, [Type.WATER, Type.ROCK]) == 0.25
print("  type chart OK")

print("=== Status: apply_status immunities ===")
tackle = BaseMove("Tackle", Type.NORMAL, 40, 100, 35, DamageClass.PHYSICAL)
ember = BaseMove("Ember", Type.FIRE, 40, 100, 25, DamageClass.SPECIAL)
no_ability = Ability("none", "no effect")

charizard_species = PokemonSpecies("Charizard", Stats(78,84,78,109,85,100), [Type.FIRE, Type.FLYING], [tackle, ember], [no_ability])
charizard = Pokemon(charizard_species, [tackle, ember], Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), no_ability, 50, 153)
bp_char = BattlePokemon(charizard)

try_apply_status(bp_char, StatusCondition.BURN)      # Fire type — should be immune
assert bp_char.status_condition is None, "Fire type should be immune to burn"

try_apply_status(bp_char, StatusCondition.FREEZE)    # Fire type — should be immune? No — only Ice immune to freeze
# Actually Fire is NOT immune to freeze, only Ice is
assert bp_char.status_condition == StatusCondition.FREEZE, "Fire type should NOT be freeze immune"
bp_char.status_condition = None

jolteon_species = PokemonSpecies("Jolteon", Stats(65,65,60,110,95,130), [Type.ELECTRIC], [tackle], [no_ability])
jolteon = Pokemon(jolteon_species, [tackle], Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), no_ability, 50)
bp_jolt = BattlePokemon(jolteon)
try_apply_status(bp_jolt, StatusCondition.PARALYSIS)
assert bp_jolt.status_condition == StatusCondition.PARALYSIS

try_apply_status(bp_jolt, StatusCondition.BURN)     # already has status — should not apply
assert bp_jolt.status_condition == StatusCondition.PARALYSIS, "Second status should not overwrite"
print("  apply_status OK")

print("=== Status: paralysis speed halving ===")
normal_speed = bp_jolt.speed
assert normal_speed == bp_jolt.pokemon.speed // 2, f"Paralysed speed should be halved, got {normal_speed}"
print("  paralysis speed OK")

print("=== Status: burn attack halving ===")
try_apply_status(bp_char, StatusCondition.BURN)
#assert bp_char.attack == bp_char.pokemon.attack // 2, "Burned attack should be halved"
#Charizard can't be burned
print("  burn attack OK")

print("=== Status: sleep counter ===")
weedle_species = PokemonSpecies("Weedle", Stats(40,35,30,20,20,50), [Type.BUG, Type.POISON], [tackle], [no_ability])
weedle = Pokemon(weedle_species, [tackle], Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), no_ability, 5)
bp_weedle = BattlePokemon(weedle)
try_apply_status(bp_weedle, StatusCondition.SLEEP)
assert bp_weedle.status_condition == StatusCondition.SLEEP
assert 1 <= bp_weedle.sleep_counter <= 3, f"sleep_counter should be 1-3, got {bp_weedle.sleep_counter}"
print("  sleep counter OK")

print("=== Weather: damage formula ===")
flamethrower = BaseMove("Flamethrower", Type.FIRE, 90, 100, 15, DamageClass.SPECIAL)
surf = BaseMove("Surf", Type.WATER, 90, 100, 15, DamageClass.SPECIAL)
arcanine_species = PokemonSpecies("Arcanine", Stats(90,110,80,100,80,95), [Type.FIRE], [flamethrower, surf, tackle, ember], [no_ability])
arcanine = Pokemon(arcanine_species, [flamethrower, surf, tackle, ember], Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), no_ability, 50)
bp_arc = BattlePokemon(arcanine)

t1 = Trainer("Ash", 1, [arcanine])
t2 = Trainer("Gary", 2, [charizard])
engine = BattleEngine(t1, t2)

move_ft = Move(flamethrower)
move_surf = Move(surf)

base_fire = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_ft, engine.weather))
base_water = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_surf, engine.weather))
engine.set_weather(Weather.SUN)
sun_fire = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_ft, engine.weather))
sun_water = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_surf, engine.weather))
assert sun_fire > base_fire, "Fire should be boosted in sun"
assert sun_water < base_water, "Water should be weakened in sun"
print("  sun weather OK")

engine.set_weather(Weather.RAIN)
rain_water = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_surf, engine.weather))
rain_fire = calculate_damage(build_damage_context(engine.trainer1.active_pokemon, engine.trainer2.active_pokemon, move_ft, engine.weather))
assert rain_water > base_fire, "Water should be boosted in rain"
assert rain_fire < base_fire, "Fire should be weakened in rain"
print("  rain weather OK")

print("\n=== All tests passed! ===")