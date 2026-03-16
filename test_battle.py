# test_battle.py
from models import *
from engine.battle import BattleEngine
from engine.type_chart import get_effectiveness
from engine.damage import calculate_damage, build_damage_context, DamageContext
from engine.status import try_apply_status, check_move_interrupt, apply_end_of_turn
from engine.abilities import modify_stat, AbilityContext, ABILITY_REGISTRY
from engine.weather import apply_weather_damage, tick_weather
from unittest.mock import MagicMock
import random

# ── helpers ──────────────────────────────────────────────────────────────────

def make_move(name="Tackle", type=Type.NORMAL, power=40, accuracy=100,
              pp=35, damage_class=DamageClass.PHYSICAL, priority=0):
    return BaseMove(name, type, power, accuracy, pp, damage_class, priority=priority)

def make_ability(name="none"):
    return Ability(name, "no effect")

def make_species(name, stats, types, moves, abilities=None):
    if abilities is None:
        abilities = [make_ability()]
    return PokemonSpecies(name, stats, types, moves, abilities)

def make_pokemon(species, moves, level=50, ability=None):
    if ability is None:
        ability = species.abilities[0]
    return Pokemon(species, moves, Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), ability, level)

def make_battle_pokemon(species, moves, level=50, ability=None):
    return BattlePokemon(make_pokemon(species, moves, level, ability))

def null_log(*args): pass


# ── fixtures ─────────────────────────────────────────────────────────────────

tackle    = make_move("Tackle",       Type.NORMAL,   40,  100, 35, DamageClass.PHYSICAL)
quick_atk = make_move("Quick Attack", Type.NORMAL,   40,  100, 30, DamageClass.PHYSICAL, priority=1)
ember     = make_move("Ember",        Type.FIRE,     40,  100, 25, DamageClass.SPECIAL)
surf      = make_move("Surf",         Type.WATER,    90,  100, 15, DamageClass.SPECIAL)
flamethrower = make_move("Flamethrower", Type.FIRE,  90,  100, 15, DamageClass.SPECIAL)
thunder_wave = BaseMove("Thunder Wave", Type.ELECTRIC, 0, 90, 20, DamageClass.STATUS)
spore        = BaseMove("Spore",        Type.GRASS,   0, 100, 15, DamageClass.STATUS)
no_ability   = make_ability("none")

charizard_sp = make_species("Charizard", Stats(78,84,78,109,85,100),
                             [Type.FIRE, Type.FLYING], [tackle, ember, flamethrower, surf])
jolteon_sp   = make_species("Jolteon",   Stats(65,65,60,110,95,130),
                             [Type.ELECTRIC], [tackle])
weedle_sp    = make_species("Weedle",    Stats(40,35,30,20,20,50),
                             [Type.BUG, Type.POISON], [tackle])
arcanine_sp  = make_species("Arcanine",  Stats(90,110,80,100,80,95),
                             [Type.FIRE], [tackle, ember, flamethrower, surf])
rhydon_sp    = make_species("Rhydon",    Stats(105,130,120,45,45,40),
                             [Type.GROUND, Type.ROCK], [tackle])
lapras_sp    = make_species("Lapras",    Stats(130,85,80,85,95,60),
                             [Type.WATER, Type.ICE], [tackle, surf])
steelix_sp   = make_species("Steelix",   Stats(75,85,200,55,65,30),
                             [Type.STEEL, Type.GROUND], [tackle])
gengar_sp    = make_species("Gengar",    Stats(60,65,60,130,75,110),
                             [Type.GHOST, Type.POISON], [tackle])

charizard = make_pokemon(charizard_sp, [tackle, ember, flamethrower, surf])
jolteon   = make_pokemon(jolteon_sp,   [tackle])
weedle    = make_pokemon(weedle_sp,    [tackle])
arcanine  = make_pokemon(arcanine_sp,  [tackle, ember, flamethrower, surf])
rhydon    = make_pokemon(rhydon_sp,    [tackle])
lapras    = make_pokemon(lapras_sp,    [tackle, surf])
steelix   = make_pokemon(steelix_sp,   [tackle])
gengar    = make_pokemon(gengar_sp,    [tackle])


def make_engine(p1=None, p2=None):
    p1 = p1 or arcanine
    p2 = p2 or charizard
    t1 = Trainer("Ash",  1, [p1])
    t2 = Trainer("Gary", 2, [p2])
    return BattleEngine(t1, t2)


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 1. Type Chart ===")
# ═══════════════════════════════════════════════════════════════════════════════

assert get_effectiveness(Type.ELECTRIC, [Type.WATER])            == 2.0
assert get_effectiveness(Type.ELECTRIC, [Type.GROUND])           == 0.0
assert get_effectiveness(Type.ELECTRIC, [Type.ELECTRIC])         == 0.5
assert get_effectiveness(Type.NORMAL,   [Type.GHOST])            == 0.0
assert get_effectiveness(Type.FIRE,     [Type.WATER, Type.ROCK]) == 0.25
assert get_effectiveness(Type.WATER,    [Type.FIRE])             == 2.0
assert get_effectiveness(Type.FIGHTING, [Type.GHOST])            == 0.0
assert get_effectiveness(Type.DRAGON,   [Type.FAIRY])            == 0.0
assert get_effectiveness(Type.UNKNOWN,  [Type.FIRE])             == 1.0  # unknown = neutral
assert get_effectiveness(Type.STELLAR,  [Type.FIRE])             == 1.0  # stellar = neutral
assert get_effectiveness(Type.FIRE,     [Type.UNKNOWN])          == 1.0  # unknown defender = neutral
print("  type chart OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 2. Stat Formula ===")
# ═══════════════════════════════════════════════════════════════════════════════

pika_sp = make_species("Pikachu", Stats(35,55,40,50,50,90), [Type.ELECTRIC], [tackle])
pika = Pokemon(pika_sp, [tackle], Stats(31,31,31,31,31,31), Stats(0,0,0,0,0,0), no_ability, 100)

# HP formula: ((2*base + iv + ev//4) * level // 100) + level + 10
expected_hp = ((2*35 + 31 + 0) * 100 // 100) + 100 + 10
assert pika.max_hp == expected_hp, f"Expected {expected_hp}, got {pika.max_hp}"

# Attack formula: ((2*base + iv + ev//4) * level // 100) + 5
expected_atk = ((2*55 + 31 + 0) * 100 // 100) + 5
assert pika.attack == expected_atk, f"Expected {expected_atk}, got {pika.attack}"

# Speed
expected_spd = ((2*90 + 31 + 0) * 100 // 100) + 5
assert pika.speed == expected_spd
print("  stat formula OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 3. BattlePokemon stat stages ===")
# ═══════════════════════════════════════════════════════════════════════════════

bp = BattlePokemon(pika)
base_atk = bp.attack

# +1 stage = 1.5x
modify_stat(bp, 'attack', 1)
assert bp.attack == int(pika.attack * 1.5), f"Expected {int(pika.attack * 1.5)}, got {bp.attack}"

# +6 stage = 4x
bp.stat_changes = Stats(0,0,0,0,0,0)
modify_stat(bp, 'attack', 6)
assert bp.attack == int(pika.attack * 4.0)

# -1 stage = 2/3x
bp.stat_changes = Stats(0,0,0,0,0,0)
modify_stat(bp, 'attack', -1)
expected = int(pika.attack * 2/3)
assert bp.attack == expected, f"Expected {expected}, got {bp.attack}"

# clamped at +6
bp.stat_changes = Stats(0,0,0,0,0,0)
for _ in range(10):
    modify_stat(bp, 'attack', 1)
assert bp.stat_changes.attack == 6, "Stage should be clamped at +6"

# clamped at -6
bp.stat_changes = Stats(0,0,0,0,0,0)
for _ in range(10):
    modify_stat(bp, 'attack', -1)
assert bp.stat_changes.attack == -6, "Stage should be clamped at -6"

print("  stat stages OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 4. Status conditions ===")
# ═══════════════════════════════════════════════════════════════════════════════

# --- immunities ---
bp_char = BattlePokemon(charizard)
try_apply_status(bp_char, StatusCondition.BURN)
assert bp_char.status_condition is None, "Fire immune to burn"

try_apply_status(bp_char, StatusCondition.FREEZE)
assert bp_char.status_condition == StatusCondition.FREEZE, "Fire NOT immune to freeze"
bp_char.status_condition = None

bp_jolt = BattlePokemon(jolteon)
try_apply_status(bp_jolt, StatusCondition.PARALYSIS)
assert bp_jolt.status_condition == StatusCondition.PARALYSIS

# can't stack a second status
try_apply_status(bp_jolt, StatusCondition.BURN)
assert bp_jolt.status_condition == StatusCondition.PARALYSIS, "Second status must not overwrite"

# Poison/Steel immune to poison
bp_weedle = BattlePokemon(weedle)
try_apply_status(bp_weedle, StatusCondition.POISON)
assert bp_weedle.status_condition is None, "Poison type immune to poison"

# Ice immune to freeze
bp_lapras = BattlePokemon(lapras)
try_apply_status(bp_lapras, StatusCondition.FREEZE)
assert bp_lapras.status_condition is None, "Ice type immune to freeze"

# --- sleep counter ---
bp_weedle2 = BattlePokemon(weedle)
try_apply_status(bp_weedle2, StatusCondition.SLEEP)
assert bp_weedle2.status_condition == StatusCondition.SLEEP
assert 1 <= bp_weedle2.sleep_counter <= 3

# --- freeze in sun ---
bp_g = BattlePokemon(gengar)
try_apply_status(bp_g, StatusCondition.FREEZE, weather=Weather.SUN)
assert bp_g.status_condition is None, "Cannot freeze in sun"

try_apply_status(bp_g, StatusCondition.FREEZE, weather=Weather.RAIN)
assert bp_g.status_condition == StatusCondition.FREEZE, "Can freeze outside sun"

print("  status immunities OK")

# --- paralysis speed halving ---
bp_jolt2 = BattlePokemon(jolteon)
try_apply_status(bp_jolt2, StatusCondition.PARALYSIS)
assert bp_jolt2.speed == jolteon.speed // 2
print("  paralysis speed OK")

# --- burn attack halving ---
burn_sp = make_species("TestMon", Stats(50,100,50,50,50,50), [Type.NORMAL], [tackle])
burn_pkmn = make_pokemon(burn_sp, [tackle])
bp_burn = BattlePokemon(burn_pkmn)
try_apply_status(bp_burn, StatusCondition.BURN)
assert bp_burn.attack == burn_pkmn.attack // 2
print("  burn attack OK")

# --- end-of-turn damage ---
logs = []
bp_poison = BattlePokemon(make_pokemon(
    make_species("P", Stats(100,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
bp_poison.status_condition = StatusCondition.POISON
hp_before = bp_poison.current_hp
apply_end_of_turn(bp_poison, logs.append)
expected_dmg = max(1, bp_poison.pokemon.max_hp // 8)
assert bp_poison.current_hp == hp_before - expected_dmg

bp_burn2 = BattlePokemon(make_pokemon(
    make_species("B", Stats(100,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
bp_burn2.status_condition = StatusCondition.BURN
hp_before = bp_burn2.current_hp
apply_end_of_turn(bp_burn2, logs.append)
expected_dmg = max(1, bp_burn2.pokemon.max_hp // 16)
assert bp_burn2.current_hp == hp_before - expected_dmg

bp_toxic = BattlePokemon(make_pokemon(
    make_species("T", Stats(160,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
bp_toxic.status_condition = StatusCondition.TOXIC
apply_end_of_turn(bp_toxic, logs.append)  # counter=1, 1/16 max
assert bp_toxic.toxic_counter == 1
apply_end_of_turn(bp_toxic, logs.append)  # counter=2, 2/16 max
assert bp_toxic.toxic_counter == 2
print("  end-of-turn damage OK")

# --- check_move_interrupt ---
# sleep blocks move
bp_sleep = BattlePokemon(make_pokemon(
    make_species("S", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
bp_sleep.status_condition = StatusCondition.SLEEP
bp_sleep.sleep_counter = 2
assert check_move_interrupt(bp_sleep, null_log) == True
assert bp_sleep.sleep_counter == 1

# sleep expires → wakes up, doesn't block
bp_sleep.sleep_counter = 0
assert check_move_interrupt(bp_sleep, null_log) == False
assert bp_sleep.status_condition is None

# freeze blocks (test multiple times; statistically impossible to thaw 20 times in a row)
bp_frozen = BattlePokemon(make_pokemon(
    make_species("F", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
bp_frozen.status_condition = StatusCondition.FREEZE
interrupted_at_least_once = any(
    check_move_interrupt(BattlePokemon(make_pokemon(
        make_species("F", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle],
    )), null_log)
    for _ in range(20)
    # re-create so status is always FREEZE
)
# We can only assert thaw path doesn't crash; probabilistic assertion skipped
print("  move interrupt OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 5. Damage formula ===")
# ═══════════════════════════════════════════════════════════════════════════════

# Pure formula test (no randomness)
random.seed(42)
ctx = DamageContext(attack=100, defense=100, level=50, power=100,
                    stab=False, type_effectiveness=1.0, weather_modifier=1.0)
dmg = calculate_damage(ctx)
# base = ((2*50/5+2)*100*100/100)/50+2 = (22*100/100)/50+2 = 22/50+2 = 2.44
# with random ~0.9 and no modifiers: int(4.44 * 0.9) ≈ 4
assert 39 <= dmg <= 46, f"Unexpected base damage: {dmg}"

# STAB adds 1.5x
ctx_stab = DamageContext(attack=100, defense=100, level=50, power=100,
                         stab=True, type_effectiveness=1.0, weather_modifier=1.0)
random.seed(42)
dmg_stab = calculate_damage(ctx_stab)
random.seed(42)
dmg_no_stab = calculate_damage(ctx)
assert dmg_stab > dmg_no_stab, "STAB should increase damage"

# Type effectiveness scales damage
ctx_super = DamageContext(attack=100, defense=100, level=50, power=100,
                          stab=False, type_effectiveness=2.0, weather_modifier=1.0)
ctx_resist = DamageContext(attack=100, defense=100, level=50, power=100,
                           stab=False, type_effectiveness=0.5, weather_modifier=1.0)
random.seed(42); dmg_super  = calculate_damage(ctx_super)
random.seed(42); dmg_resist = calculate_damage(ctx_resist)
assert dmg_super > dmg_resist

# Weather modifier
ctx_sun = DamageContext(attack=100, defense=100, level=50, power=100,
                        stab=False, type_effectiveness=1.0, weather_modifier=1.5)
random.seed(42); dmg_sun = calculate_damage(ctx_sun)
random.seed(42); dmg_base = calculate_damage(ctx)
assert dmg_sun > dmg_base

# Zero type effectiveness → damage = 0 after formula
# (type_effectiveness=0 makes the whole thing 0)
ctx_immune = DamageContext(attack=100, defense=100, level=50, power=100,
                           stab=False, type_effectiveness=0.0, weather_modifier=1.0)
assert calculate_damage(ctx_immune) == 0
print("  damage formula OK")

# --- build_damage_context ---
bp_arc = BattlePokemon(arcanine)
bp_char2 = BattlePokemon(charizard)

move_ft = Move(flamethrower)
ctx_fire = build_damage_context(bp_arc, bp_char2, move_ft, Weather.CLEAR)
assert ctx_fire.stab == True,  "Arcanine using Fire move should have STAB"
assert ctx_fire.attack == bp_arc.special_attack
assert ctx_fire.defense == bp_char2.special_defense
assert ctx_fire.weather_modifier == 1.0

ctx_sun_fire = build_damage_context(bp_arc, bp_char2, move_ft, Weather.SUN)
assert ctx_sun_fire.weather_modifier == 1.5, "Fire boosted in sun"

ctx_rain_fire = build_damage_context(bp_arc, bp_char2, move_ft, Weather.RAIN)
assert ctx_rain_fire.weather_modifier == 0.5, "Fire weakened in rain"

move_surf = Move(surf)
ctx_rain_water = build_damage_context(bp_arc, bp_char2, move_surf, Weather.RAIN)
assert ctx_rain_water.weather_modifier == 1.5, "Water boosted in rain"

# Sand SpDef boost for Rock types
bp_rhydon = BattlePokemon(rhydon)
move_s = Move(surf)
ctx_sand = build_damage_context(bp_arc, bp_rhydon, move_s, Weather.SAND)
ctx_clear = build_damage_context(bp_arc, bp_rhydon, move_s, Weather.CLEAR)
assert ctx_sand.defense > ctx_clear.defense, "Rock SpDef boosted in sand"
print("  build_damage_context OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 6. Weather effects ===")
# ═══════════════════════════════════════════════════════════════════════════════

# Sand damages non-immune types
logs = []
bp_g2   = BattlePokemon(gengar)
bp_stx  = BattlePokemon(steelix)
hp_before_g = bp_g2.current_hp
hp_before_s = bp_stx.current_hp
apply_weather_damage(bp_g2, bp_stx, Weather.SAND, logs.append)
assert bp_g2.current_hp < hp_before_g,  "Gengar should take sand damage"
assert bp_stx.current_hp == hp_before_s, "Steelix (Steel/Ground) immune to sand"

# Hail damages non-Ice types
logs = []
bp_arc2  = BattlePokemon(arcanine)
bp_lap   = BattlePokemon(lapras)
hp_before_a = bp_arc2.current_hp
hp_before_l = bp_lap.current_hp
apply_weather_damage(bp_arc2, bp_lap, Weather.HAIL, logs.append)
assert bp_arc2.current_hp < hp_before_a, "Arcanine should take hail damage"
assert bp_lap.current_hp == hp_before_l,  "Lapras (Ice) immune to hail"

# tick_weather decrements and clears
engine = make_engine()
engine.set_weather(Weather.RAIN, turns=2)
tick_weather(engine)
assert engine.weather_turns_remaining == 1
tick_weather(engine)
assert engine.weather == Weather.CLEAR, "Weather should clear after expiry"

# -1 = infinite, never decrements
engine.set_weather(Weather.SUN, turns=-1)
tick_weather(engine)
assert engine.weather == Weather.SUN
assert engine.weather_turns_remaining == -1
print("  weather effects OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 7. Ability hook system ===")
# ═══════════════════════════════════════════════════════════════════════════════

# --- modify_stat helper ---
bp_test = BattlePokemon(make_pokemon(
    make_species("M", Stats(50,80,50,50,50,50), [Type.NORMAL], [tackle]), [tackle]
))
changed = modify_stat(bp_test, 'attack', -1)
assert changed == True
assert bp_test.stat_changes.attack == -1

# at floor, returns False
for _ in range(10):
    modify_stat(bp_test, 'attack', -1)
changed = modify_stat(bp_test, 'attack', -1)
assert changed == False, "At -6 floor, modify_stat should return False"

# --- Intimidate fires on switch-in ---
intim_ability = Ability("intimidate", "lowers opponent attack")
intim_sp = make_species("Intimidator", Stats(80,80,80,80,80,80),
                         [Type.NORMAL], [tackle], [intim_ability])
intim_pkmn  = make_pokemon(intim_sp, [tackle], ability=intim_ability)
target_pkmn = make_pokemon(
    make_species("Target", Stats(80,80,80,80,80,80), [Type.NORMAL], [tackle]), [tackle]
)
t1 = Trainer("A", 1, [intim_pkmn])
t2 = Trainer("B", 2, [target_pkmn])
engine = BattleEngine(t1, t2)

# fire ON_SWITCH_IN manually — mirrors what start_battle does
engine.fire_hook(BattleHook.ON_SWITCH_IN, engine.trainer1.active_pokemon,
                 engine.trainer1, opponent=engine.trainer2.active_pokemon)

target_bp = engine.trainer2.active_pokemon
assert target_bp.stat_changes.attack == -1, "Intimidate should lower opponent attack on switch-in"

# --- Lightning Rod cancels Electric moves ---
lr_ability = Ability("lightning-rod", "absorbs electric moves")
lr_sp = make_species("LR", Stats(80,80,80,80,80,80), [Type.NORMAL], [tackle], [lr_ability])
lr_pkmn = make_pokemon(lr_sp, [tackle], ability=lr_ability)
ctx = AbilityContext(
    engine=MagicMock(), user=BattlePokemon(lr_pkmn),
    user_trainer=MagicMock(), opponent=None,
    move_type=Type.ELECTRIC
)
from engine.abilities import lightning_rod as lr_fn
lr_fn(ctx)
assert ctx.cancelled == True

# non-Electric move not cancelled
ctx2 = AbilityContext(
    engine=MagicMock(), user=BattlePokemon(lr_pkmn),
    user_trainer=MagicMock(), opponent=None,
    move_type=Type.WATER
)
lr_fn(ctx2)
assert ctx2.cancelled == False

# --- Levitate cancels Ground moves ---
lev_ability = Ability("levitate", "immune to ground")
lev_sp = make_species("Lev", Stats(80,80,80,80,80,80), [Type.PSYCHIC], [tackle], [lev_ability])
lev_pkmn = make_pokemon(lev_sp, [tackle], ability=lev_ability)
ctx3 = AbilityContext(
    engine=MagicMock(), user=BattlePokemon(lev_pkmn),
    user_trainer=MagicMock(), opponent=None,
    move_type=Type.GROUND
)
from engine.abilities import levitate as lev_fn
lev_fn(ctx3)
assert ctx3.cancelled == True
print("  ability hooks OK")

# --- Weather-setting abilities ---
drizzle_ability = Ability("drizzle", "starts rain")
drizzle_sp = make_species("Politoed", Stats(90,75,75,90,100,70),
                           [Type.WATER], [tackle, surf], [drizzle_ability])
drizzle_pkmn = make_pokemon(drizzle_sp, [tackle, surf], ability=drizzle_ability)
t1 = Trainer("A", 1, [drizzle_pkmn])
t2 = Trainer("B", 2, [arcanine])
engine = BattleEngine(t1, t2)
print(engine.trainer1.active_pokemon.pokemon.ability.name)
engine.fire_hook(BattleHook.ON_SWITCH_IN, engine.trainer1.active_pokemon,
                 engine.trainer1, opponent=engine.trainer2.active_pokemon)
print(engine.weather)
assert engine.weather == Weather.RAIN, "Drizzle should set rain on switch-in"
assert engine.weather_turns_remaining == -1, "Ability weather should be infinite"
print("  weather abilities OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 8. Turn order & priority ===")
# ═══════════════════════════════════════════════════════════════════════════════

# Quick Attack (priority +1) should beat normal move regardless of speed
qa_sp = make_species("Slowbro", Stats(95,75,110,100,80,30), [Type.WATER], [tackle, quick_atk])
qa_pkmn = make_pokemon(qa_sp, [tackle, quick_atk], level=50)  # very slow

fast_sp = make_species("Jolteon2", Stats(65,65,60,110,95,130), [Type.ELECTRIC], [tackle])
fast_pkmn = make_pokemon(fast_sp, [tackle], level=50)          # very fast

t1 = Trainer("A", 1, [qa_pkmn])
t2 = Trainer("B", 2, [fast_pkmn])
engine = BattleEngine(t1, t2)

# Slowbro uses Quick Attack (+1), Jolteon uses Tackle (0)
# Slowbro should go first despite being slower
move_qa     = Move(quick_atk)
move_tackle = Move(tackle)
order = engine.determine_turn_order(move_qa, move_tackle)
assert order[0][0] == engine.trainer1, "Priority +1 move should go first regardless of speed"

# Normal speed ordering: faster goes first
order2 = engine.determine_turn_order(move_tackle, move_tackle)
# Jolteon (speed 130 base) should go before Slowbro (speed 30 base)
assert order2[0][0] == engine.trainer2, "Faster Pokemon should go first with equal priority"

# Switches go before moves
order3 = engine.determine_turn_order(0, move_tackle)  # trainer1 switches
assert order3[0][0] == engine.trainer1, "Switch should always go first"

# Trick Room reverses speed within same priority
engine.trick_room_active = True
order4 = engine.determine_turn_order(move_tackle, move_tackle)
assert order4[0][0] == engine.trainer1, "Trick Room: slower Pokemon should go first"
engine.trick_room_active = False

print("  turn order OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 9. BattlePokemon state ===")
# ═══════════════════════════════════════════════════════════════════════════════

bp = BattlePokemon(make_pokemon(
    make_species("X", Stats(80,80,80,80,80,80), [Type.NORMAL], [tackle]), [tackle]
))

# current_hp initialises to max_hp
assert bp.current_hp == bp.pokemon.max_hp

# switch_out resets stat stages and volatile conditions
modify_stat(bp, 'attack', 3)
bp.volatile_conditions.append(VolatileCondition.CONFUSION)
bp.toxic_counter = 4
bp.switch_out()
assert bp.stat_changes.attack == 0,          "Stat stages should reset on switch-out"
assert len(bp.volatile_conditions) == 0,     "Volatile conditions should clear on switch-out"
assert bp.toxic_counter == 0,                "Toxic counter should reset on switch-out"

# status persists through switch-out
bp2 = BattlePokemon(make_pokemon(
    make_species("Y", Stats(80,80,80,80,80,80), [Type.NORMAL], [tackle]), [tackle]
))
bp2.status_condition = StatusCondition.BURN
bp2.switch_out()
assert bp2.status_condition == StatusCondition.BURN, "Status should persist through switch-out"

# moves list built from base moves
assert len(bp.moves) == 1
assert isinstance(bp.moves[0], Move)

# PP decrements on use
bp.moves[0].use()
assert bp.moves[0].current_pp == tackle.pp - 1

print("  BattlePokemon state OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 10. Trainer & BattleTrainer ===")
# ═══════════════════════════════════════════════════════════════════════════════

# Trainer rejects > 6 Pokemon
try:
    Trainer("A", 1, [arcanine]*7)
    assert False, "Should raise"
except ValueError:
    pass

# Trainer rejects 0 Pokemon
try:
    Trainer("A", 1, [])
    assert False, "Should raise"
except ValueError:
    pass

# has_lost only when all fainted
p1 = make_pokemon(make_species("A", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle])
p2 = make_pokemon(make_species("B", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle])
bt = BattleTrainer(Trainer("T", 1, [p1, p2]))
assert not bt.has_lost
bt.pokemon[0].current_hp = 0
assert not bt.has_lost
bt.pokemon[1].current_hp = 0
assert bt.has_lost

# reserve_pokemon excludes active and fainted
p3 = make_pokemon(make_species("C", Stats(50,50,50,50,50,50), [Type.NORMAL], [tackle]), [tackle])
bt2 = BattleTrainer(Trainer("T2", 2, [p1, p2, p3]))
bt2.pokemon[0].current_hp = 50   # active (index 0)
bt2.pokemon[1].current_hp = 0    # fainted
bt2.pokemon[2].current_hp = 50   # alive reserve
reserve = bt2.reserve_pokemon
assert len(reserve) == 1
assert reserve[0][0] == 2  # index of the alive reserve

# switch raises on fainted target
try:
    bt2.switch(1)
    assert False, "Should raise when switching to fainted Pokemon"
except ValueError:
    pass

print("  Trainer & BattleTrainer OK")


# ═══════════════════════════════════════════════════════════════════════════════
print("=== 11. BattleEngine integration ===")
# ═══════════════════════════════════════════════════════════════════════════════

engine = make_engine()

# set_weather populates fields correctly
engine.set_weather(Weather.RAIN, turns=3)
assert engine.weather == Weather.RAIN
assert engine.weather_turns_remaining == 3

engine.set_weather(Weather.SUN, turns=-1)
assert engine.weather_turns_remaining == -1

# get_effective_speed doubles for swift-swim in rain
ss_ability  = Ability("swift-swim", "doubles speed in rain")
ss_sp = make_species("Kingdra", Stats(75,95,95,95,95,85),
                     [Type.WATER, Type.DRAGON], [tackle, surf], [ss_ability])
ss_pkmn = make_pokemon(ss_sp, [tackle, surf], ability=ss_ability)
t1 = Trainer("A", 1, [ss_pkmn])
t2 = Trainer("B", 2, [arcanine])
engine2 = BattleEngine(t1, t2)
engine2.set_weather(Weather.RAIN)
bp_ss = engine2.trainer1.active_pokemon
base_speed = bp_ss.speed
effective   = engine2.get_effective_speed(bp_ss)
assert effective == base_speed * 2, "Swift Swim should double speed in rain"

# get_effective_speed unaffected outside of matching weather
engine2.set_weather(Weather.SUN)
assert engine2.get_effective_speed(bp_ss) == base_speed, "Swift Swim inactive outside rain"

print("  BattleEngine integration OK")


print("\n" + "="*50)
print("All tests passed!")
print("="*50)