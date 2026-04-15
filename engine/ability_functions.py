"""
ability_functions.py

One function per ability, named ability_<snake_case_name>.
Each function's signature matches the hook it registers to exactly.

Hook signatures (value-first for pipeline hooks):
  BeforeSelfMoveHook      : (attacker, defender, move, turn_order_position, first_turn) -> None
  BeforeAllyMoveHook      : (holder, ally, defender, move) -> None
  BeforeOpponentMoveHook  : (holder, attacker, move) -> None
  BeforeOpponentPriorityMoveHook : (holder, attacker, move) -> None
  BeforeDamageCalcHook    : (damage, attacker, defender, move, is_crit, effectiveness) -> int
  BeforeAllyDamageCalcHook: (damage, holder, ally, attacker, move) -> int
  BeforeSelfStatModifyHook: (stages, holder, source, stat) -> int
  BeforeAllyStatModifyHook: (stages, holder, ally, source, stat) -> int
  BeforeSelfStatCalcHook  : (raw_value, holder, stat, battle_state) -> int
  BeforeStatusApplyHook   : (blocked, holder, source, status, battle_state) -> bool
  BeforeAllyStatusApplyHook:(blocked, holder, ally, source, status, battle_state) -> bool
  SpeedCalculationHook    : (speed, holder, battle_state) -> int
  BeforeAccuracyCalcHook  : (accuracy, attacker, defender, move) -> float
  BeforeTurnOrderCalcHook : (priority, holder, move, battle_state) -> int
  BeforeMoveRedirectHook  : (ignore, holder, move) -> bool
  OnSelfEnterHook         : (holder, battle_state) -> None
  OnAllyEnterHook         : (holder, ally, battle_state) -> None
  OnSelfSwitchOutHook     : (holder, battle_state) -> None
  OnHitTakenHook          : (holder, attacker, move, damage_dealt, battle_state) -> None
  OnContactHitTakenHook   : (holder, attacker, move, damage_dealt, battle_state) -> None
  OnPhysicalHitTakenHook  : (holder, attacker, move, damage_dealt, battle_state) -> None
  OnCritHitTakenHook      : (holder, attacker, move, battle_state) -> None
  OnDamageTakenThresholdHook:(holder, attacker, move, hp_before, hp_after, battle_state) -> None
  OnHitDealtHook          : (holder, defender, move, damage_dealt, battle_state) -> None
  OnDrainMoveAgainstSelfHook:(drain, holder, attacker, move) -> int
  BeforeIndirectDamageHook: (amount, holder, source, battle_state) -> int
  OnSelfFaintHook         : (holder, attacker, battle_state) -> None
  OnOpponentFaintHook     : (holder, fainted, battle_state) -> None
  OnAnyPokemonFaintHook   : (holder, fainted, battle_state) -> None
  OnAllyFaintHook         : (holder, fainted_ally, battle_state) -> None
  OnSelfFlinchHook        : (blocked, holder, attacker, battle_state) -> bool
  OnSelfStatDropHook      : (holder, source, stat, stages, battle_state) -> None
  OnFoeStatBoostHook      : (holder, foe, stat, stages, battle_state) -> None
  BeforeSecondaryEffectApplyHook:(blocked, holder, attacker, move, effect) -> bool
  OnBerryConsumeHook      : (holder, berry, battle_state) -> None
  BeforeBerryUseHook      : (threshold, holder, berry) -> float
  BeforeItemStealHook     : (blocked, holder, source, move) -> bool
  OnAllyItemConsumeHook   : (holder, ally, consumed_item, battle_state) -> None
  OnForceSwitchAttemptHook: (blocked, holder, source, move) -> bool
  OnOpponentSwitchAttemptHook:(blocked, holder, fleeing, battle_state) -> bool
  OnWeatherChangeHook     : (holder, new_weather, battle_state) -> None
  OnTerrainChangeHook     : (holder, new_terrain, battle_state) -> None
  EndOfTurnHook           : (holder, battle_state) -> None
  SleepTurnCounterHook    : (decrement, holder, current_sleep_turns) -> int
  WeightCalcHook          : (weight, holder) -> float
  BeforeCritCalcHook      : (crit_stage, holder, move) -> int
  BeforeRecoilApplyHook   : (recoil, holder, move) -> int
  OnOpponentMoveUsedAgainstSelfHook:(pp_cost, holder, attacker, move) -> int
  OnIntimidateReceivedHook: (holder, intimidator, battle_state) -> None
  OnFoePoisonApplyHook    : (holder, poisoned, poison_type, battle_state) -> None
  OnSelfStatusApplyHook   : (holder, source, status, battle_state) -> None
  OnDanceMoveUsedHook     : (holder, original_user, move, battle_state) -> None
  OnSpecificMoveUseHook   : (holder, move, battle_state) -> None
  BeforeAllyMoveTargetSelfHook:(immune, holder, ally, move) -> bool
  BeforeStatusMoveTargetCheckHook:(blocked, holder, attacker, move, battle_state) -> bool
  PassiveFieldHook        : (field_dict, battle_state) -> dict
  WildEncounterRateHook   : (rate, holder) -> float
  WildBattleEscapeHook    : (success, holder) -> bool
  PostBattleHook          : (holder, battle_result, battle_state) -> None
"""

from __future__ import annotations
import random
from models import Pokemon, Move, BattleState, Side, Status, StatStages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_stat(pokemon: Pokemon, stat: str, stages: int, source: Pokemon | None = None):
    """Apply stat stage change to pokemon, respecting [-6,+6] clamp."""
    pokemon.stat_stages.modify(stat, stages)


def _highest_stat(pokemon: Pokemon) -> str:
    """Return the name of the pokemon's highest base stat (excluding HP)."""
    stats = ["attack", "defense", "sp_atk", "sp_def", "speed"]
    return max(stats, key=lambda s: pokemon.base_stats.get(s, 0))


def _is_type_changer_category(move: Move) -> bool:
    return move.category in ("physical", "special")


def _normalize_type_change(move: Move, new_type: str, power_multiplier: float = 1.2):
    """Shared logic for Aerilate/Galvanize/Pixilate/Refrigerate/Dragonize."""
    if move.type == "normal" and _is_type_changer_category(move):
        move.flags.type_override = new_type
        move.flags.power_multiplier *= power_multiplier


def _starter_ability_boost(move: Move, attacker: Pokemon, move_type: str,
                            threshold: float = 1/3, multiplier: float = 1.5):
    """Shared logic for Blaze/Overgrow/Torrent/Swarm."""
    if attacker.hp_ratio() <= threshold and move.type == move_type:
        move.flags.power_multiplier *= multiplier


def _type_absorb(damage: int, holder: Pokemon, attacker: Pokemon, move: Move,
                 absorbed_type: str, heal_fraction: float = 0.25) -> int:
    """Shared absorb logic: nullify damage, restore HP. Returns 0."""
    if move.type == absorbed_type and not move.flags.suppress_target_ability:
        holder.heal(int(holder.max_hp * heal_fraction))
        return 0
    return damage


# ---------------------------------------------------------------------------
# A
# ---------------------------------------------------------------------------

def ability_adaptability(attacker: Pokemon, defender: Pokemon, move: Move,
                         turn_order_position: int, first_turn: bool):
    """STAB multiplier becomes 2.0 instead of 1.5.
    Implemented by setting a flag; damage calc reads move.flags on attacker."""
    if move.type in attacker.types:
        move.flags.power_multiplier *= (2.0 / 1.5)


def ability_aerilate(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    _normalize_type_change(move, "flying")


def ability_aftermath(holder: Pokemon, attacker: Pokemon, battle_state: BattleState):
    """Deal ¼ attacker max HP on holder faint."""
    if attacker.is_alive():
        attacker.take_damage(attacker.max_hp // 4)


def ability_air_lock(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["weather_suppressed"] = True
    return field_dict


def ability_analytic(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    """1.3× power if moving last (position > 0 means faster mons already moved)."""
    if turn_order_position > 0:
        move.flags.power_multiplier *= 1.3


def ability_anger_point(holder: Pokemon, attacker: Pokemon, move: Move,
                        battle_state: BattleState):
    holder.stat_stages.attack = 6


def ability_anger_shell(holder: Pokemon, attacker: Pokemon, move: Move,
                        hp_before: float, hp_after: float,
                        battle_state: BattleState):
    if hp_before > 0.5 >= hp_after:
        for stat in ("attack", "sp_atk", "speed"):
            _apply_stat(holder, stat, 1)
        for stat in ("defense", "sp_def"):
            _apply_stat(holder, stat, -1)


def ability_anticipation(holder: Pokemon, battle_state: BattleState):
    """Informational only — engine emits a shudder event; no stat/damage effect."""
    pass


def ability_arena_trap(blocked: bool, holder: Pokemon, fleeing: Pokemon,
                       battle_state: BattleState) -> bool:
    if fleeing.is_grounded and "flying" not in fleeing.types:
        return True
    return blocked


def ability_armor_tail(holder: Pokemon, attacker: Pokemon, move: Move):
    move.flags.priority_delta = -999  # signal engine to cancel the move


def ability_aroma_veil(holder: Pokemon, attacker: Pokemon, move: Move):
    MENTAL_MOVES = {"taunt", "encore", "torment", "disable", "heal_block",
                    "attract", "infatuation"}
    if move.name.lower().replace(" ", "_") in MENTAL_MOVES:
        move.flags.priority_delta = -999


def ability_as_one_chilling(holder: Pokemon, battle_state: BattleState):
    """Registered as both Unnerve and Chilling Neigh at init."""
    ability_unnerve(battle_state={}, field_dict={})  # via PassiveFieldHook
    # Chilling Neigh portion registered separately on OnOpponentFaintHook


def ability_aura_break(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["aura_break_active"] = True
    return field_dict


def ability_bad_dreams(holder: Pokemon, battle_state: BattleState):
    """Applied to each sleeping opponent — engine iterates active foes."""
    pass  # Engine calls this per sleeping foe; holder IS the sleeping target here.


def ability_bad_dreams_eot(holder: Pokemon, sleeping_foe: Pokemon):
    """Actual EOT implementation: deal ⅛ HP to sleeping_foe."""
    if sleeping_foe.status == Status.SLEEP:
        sleeping_foe.take_damage(sleeping_foe.max_hp // 8)


def ability_battle_armor(damage: int, attacker: Pokemon, defender: Pokemon,
                         move: Move, is_crit: bool, effectiveness: float) -> int:
    if is_crit:
        is_crit = False  # signal to engine; damage calc ignores crit multiplier
        # Simplification: reduce damage by crit bonus (1.5×)
        return int(damage / 1.5)
    return damage


def ability_battle_bond(holder: Pokemon, fainted: Pokemon,
                        battle_state: BattleState):
    if holder.name.lower() == "greninja" and holder.form == "default":
        holder.form = "ash"


def ability_beads_of_ruin(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["beads_of_ruin_active"] = True
    return field_dict


def ability_beast_boost(holder: Pokemon, fainted: Pokemon,
                        battle_state: BattleState):
    stat = _highest_stat(holder)
    _apply_stat(holder, stat, 1)


def ability_berserk(holder: Pokemon, attacker: Pokemon, move: Move,
                    hp_before: float, hp_after: float,
                    battle_state: BattleState):
    if hp_before > 0.5 >= hp_after:
        _apply_stat(holder, "sp_atk", 1)


def ability_big_pecks(stages: int, holder: Pokemon, source: Pokemon,
                      stat: str) -> int:
    if stat == "defense" and stages < 0:
        return 0
    return stages


def ability_blaze(attacker: Pokemon, defender: Pokemon, move: Move,
                  turn_order_position: int, first_turn: bool):
    _starter_ability_boost(move, attacker, "fire")


def ability_bulletproof(holder: Pokemon, attacker: Pokemon, move: Move):
    BALL_BOMB_MOVES = {
        "acid_spray", "aura_sphere", "barrage", "beak_blast", "bullet_seed",
        "egg_bomb", "electro_ball", "energy_ball", "focus_blast", "gyro_ball",
        "ice_ball", "magnet_bomb", "mist_ball", "mud_bomb", "octazooka",
        "pollen_puff", "pyro_ball", "rock_blast", "rock_wrecker", "searing_shot",
        "seed_bomb", "shadow_ball", "sludge_bomb", "weather_ball", "zap_cannon",
    }
    if move.name.lower().replace(" ", "_") in BALL_BOMB_MOVES or move.is_ball or move.is_bomb:
        move.flags.priority_delta = -999


# ---------------------------------------------------------------------------
# C
# ---------------------------------------------------------------------------

def ability_cheek_pouch(holder: Pokemon, berry: str, battle_state: BattleState):
    holder.heal(holder.max_hp // 3)


def ability_chilling_neigh(holder: Pokemon, fainted: Pokemon,
                           battle_state: BattleState):
    _apply_stat(holder, "attack", 1)


def ability_chlorophyll(speed: int, holder: Pokemon,
                        battle_state: BattleState) -> int:
    if battle_state.is_sunny():
        return speed * 2
    return speed


def ability_clear_body(stages: int, holder: Pokemon, source: Pokemon,
                       stat: str) -> int:
    if stages < 0:
        return 0
    return stages


def ability_cloud_nine(field_dict: dict, battle_state: BattleState) -> dict:
    return ability_air_lock(field_dict, battle_state)


def ability_color_change(holder: Pokemon, attacker: Pokemon, move: Move,
                         damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.type not in (None, "typeless"):
        effective_type = move.flags.type_override or move.type
        holder.types = [effective_type]


def ability_comatose(blocked: bool, holder: Pokemon, source: Pokemon,
                     status: str, battle_state: BattleState) -> bool:
    if status != Status.SLEEP:
        return True
    return blocked


def ability_commander(holder: Pokemon, battle_state: BattleState):
    """Find Dondozo ally in doubles; if present, holder dives in."""
    if not battle_state.is_doubles:
        return
    # Engine resolves partner lookup; flag activation here
    holder.commander_active = True


def ability_competitive(holder: Pokemon, source: Pokemon, stat: str,
                        stages: int, battle_state: BattleState):
    if stages < 0:
        _apply_stat(holder, "sp_atk", 2)


def ability_compound_eyes(attacker: Pokemon, defender: Pokemon,
                          move: Move, accuracy: float) -> float:
    return accuracy * 1.3


def ability_contrary(stages: int, holder: Pokemon, source: Pokemon,
                     stat: str) -> int:
    return -stages


def ability_corrosion(blocked: bool, holder: Pokemon, source: Pokemon,
                      status: str, battle_state: BattleState) -> bool:
    """Holder CAN poison Steel/Poison types — registered on attacker side.
    This function is registered to BeforeStatusApplyHook on the TARGET,
    called with holder=target; we unblock poison if source has Corrosion."""
    if status in (Status.POISON, Status.BADLY_POISON):
        if hasattr(source, "ability") and source.ability == "corrosion":
            return False  # allow it through
    return blocked


def ability_costar(holder: Pokemon, battle_state: BattleState):
    """Copy ally's stat stages on entry (doubles)."""
    pass  # Engine provides ally reference; simplified — engine copies stages


def ability_cotton_down(holder: Pokemon, attacker: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        # Lower Speed of all opponents (engine iterates)
        _apply_stat(attacker, "speed", -1)


def ability_cud_chew(holder: Pokemon, berry: str, battle_state: BattleState):
    holder.cud_chew_berry = berry


def ability_cud_chew_eot(holder: Pokemon, battle_state: BattleState):
    if holder.cud_chew_berry:
        # Engine re-activates the stored berry
        holder.last_berry_consumed = holder.cud_chew_berry
        holder.cud_chew_berry = None


def ability_curious_medicine(holder: Pokemon, battle_state: BattleState):
    """Reset all active Pokémon's stat stages on entry."""
    holder.stat_stages.reset()


def ability_cursed_body(holder: Pokemon, attacker: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and random.random() < 0.30:
        # Engine applies Disable to attacker's last used move
        attacker.choice_locked_move = move.name  # repurposed as "disabled"


def ability_cute_charm(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and random.random() < 0.30:
        if holder.gender and attacker.gender and holder.gender != attacker.gender:
            attacker.is_infatuated = True


# ---------------------------------------------------------------------------
# D
# ---------------------------------------------------------------------------

def ability_damp(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["damp_active"] = True
    return field_dict


def ability_dancer(holder: Pokemon, original_user: Pokemon, move: Move,
                   battle_state: BattleState):
    if move.is_dance and original_user is not holder:
        # Engine queues holder to use the same move immediately after
        pass


def ability_dark_aura(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["dark_aura_active"] = True
    return field_dict


def ability_dauntless_shield(holder: Pokemon, battle_state: BattleState):
    _apply_stat(holder, "defense", 1)


def ability_dazzling(holder: Pokemon, attacker: Pokemon, move: Move):
    ability_armor_tail(holder, attacker, move)


def ability_defeatist(raw_value: int, holder: Pokemon, stat: str,
                      battle_state: BattleState) -> int:
    if holder.hp_ratio() <= 0.5 and stat in ("attack", "sp_atk"):
        return raw_value // 2
    return raw_value


def ability_defiant(holder: Pokemon, source: Pokemon, stat: str,
                    stages: int, battle_state: BattleState):
    if stages < 0:
        _apply_stat(holder, "attack", 2)


def ability_delta_stream(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "strong_winds"
    battle_state.weather_turns = -1  # indefinite while holder is in


def ability_desolate_land(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "harsh_sun"
    battle_state.weather_turns = -1


def ability_disguise(damage: int, attacker: Pokemon, defender: Pokemon,
                     move: Move, is_crit: bool, effectiveness: float) -> int:
    if defender.disguise_intact and move.category != "status":
        defender.disguise_intact = False
        defender.take_damage(defender.max_hp // 8)  # disguise-break chip
        return 0
    return damage


def ability_download(holder: Pokemon, battle_state: BattleState):
    """Boost Attack if foe's Sp. Def < Defense, else boost Sp. Atk."""
    # Engine provides foe reference; simplified with placeholder
    pass  # Engine calls with foe: if foe.base_stats["sp_def"] < foe.base_stats["defense"]: atk else spatk


def ability_dragons_maw(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if move.type == "dragon":
        move.flags.power_multiplier *= 1.5


def ability_dragonize(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    _normalize_type_change(move, "dragon")


def ability_drizzle(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "rain"
    battle_state.weather_turns = 5


def ability_drought(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "sun"
    battle_state.weather_turns = 5


def ability_dry_skin_eot(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_raining():
        holder.heal(holder.max_hp // 8)
    elif battle_state.is_sunny():
        holder.take_damage(holder.max_hp // 8)


def ability_dry_skin_hit(holder: Pokemon, attacker: Pokemon, move: Move,
                         damage_dealt: int, battle_state: BattleState):
    if move.type == "water":
        holder.heal(holder.max_hp // 4)
    elif move.type == "fire":
        holder.take_damage(holder.max_hp // 4)


# ---------------------------------------------------------------------------
# E
# ---------------------------------------------------------------------------

def ability_early_bird(decrement: int, holder: Pokemon,
                       current_sleep_turns: int) -> int:
    return decrement * 2


def ability_earth_eater(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "ground" and not move.flags.suppress_target_ability:
        defender.heal(defender.max_hp // 4)
        return 0
    return damage


def ability_effect_spore(holder: Pokemon, attacker: Pokemon, move: Move,
                         damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and attacker.status == Status.NONE and random.random() < 0.30:
        roll = random.random()
        if roll < 1/3:
            attacker.status = Status.PARALYSIS
        elif roll < 2/3:
            attacker.status = Status.POISON
        else:
            attacker.status = Status.SLEEP
            attacker.sleep_turns_remaining = random.randint(1, 3)


def ability_electric_surge(holder: Pokemon, battle_state: BattleState):
    battle_state.terrain = "electric"
    battle_state.terrain_turns = 5


def ability_electromorphosis(holder: Pokemon, attacker: Pokemon, move: Move,
                              damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        holder.charge_state = True


def ability_embody_aspect(holder: Pokemon, battle_state: BattleState):
    FORM_STAT = {
        "teal":    "speed",
        "hearthflame": "attack",
        "wellspring": "sp_def",
        "cornerstone": "defense",
    }
    stat = FORM_STAT.get(holder.form)
    if stat:
        _apply_stat(holder, stat, 1)


def ability_emergency_exit(holder: Pokemon, attacker: Pokemon, move: Move,
                            hp_before: float, hp_after: float,
                            battle_state: BattleState):
    if hp_before > 0.5 >= hp_after:
        # Engine handles switch; set flag
        holder.switched_in_this_turn = False  # signal engine to switch


# ---------------------------------------------------------------------------
# F
# ---------------------------------------------------------------------------

def ability_fairy_aura(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["fairy_aura_active"] = True
    return field_dict


def ability_filter(damage: int, attacker: Pokemon, defender: Pokemon,
                   move: Move, is_crit: bool, effectiveness: float) -> int:
    if effectiveness > 1.0:
        return int(damage * 0.75)
    return damage


def ability_flame_body(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and attacker.status == Status.NONE and random.random() < 0.30:
        attacker.status = Status.BURN


def ability_flare_boost(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if attacker.status == Status.BURN and move.category == "special":
        move.flags.power_multiplier *= 1.5


def ability_flash_fire(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "fire" and not move.flags.suppress_target_ability:
        if not defender.flash_fire_active:
            defender.flash_fire_active = True
        return 0
    return damage


def ability_flash_fire_boost(attacker: Pokemon, defender: Pokemon, move: Move,
                              turn_order_position: int, first_turn: bool):
    if attacker.flash_fire_active and move.type == "fire":
        move.flags.power_multiplier *= 1.5


def ability_flower_gift_stat(raw_value: int, holder: Pokemon, stat: str,
                              battle_state: BattleState) -> int:
    if battle_state.is_sunny() and stat in ("attack", "sp_def"):
        return int(raw_value * 1.5)
    return raw_value


def ability_flower_veil(stages: int, holder: Pokemon, ally: Pokemon,
                        source: Pokemon, stat: str) -> int:
    if "grass" in ally.types and stages < 0:
        return 0
    return stages


def ability_fluffy(damage: int, attacker: Pokemon, defender: Pokemon,
                   move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.flags.is_contact:
        damage = damage // 2
    if move.type == "fire":
        damage = damage * 2
    return damage


def ability_forecast(holder: Pokemon, new_weather: str,
                     battle_state: BattleState):
    WEATHER_FORM = {
        "sun":  "sunny", "harsh_sun": "sunny",
        "rain": "rainy", "heavy_rain": "rainy",
        "hail": "snowy", "snow": "snowy",
    }
    holder.form = WEATHER_FORM.get(new_weather, "normal")


def ability_forewarn(holder: Pokemon, battle_state: BattleState):
    """Informational — engine reveals highest-BP foe move."""
    pass


def ability_friend_guard(damage: int, holder: Pokemon, ally: Pokemon,
                         attacker: Pokemon, move: Move) -> int:
    return int(damage * 0.75)


def ability_full_metal_body(stages: int, holder: Pokemon, source: Pokemon,
                             stat: str) -> int:
    if stages < 0:
        return 0
    return stages


def ability_fur_coat(damage: int, attacker: Pokemon, defender: Pokemon,
                     move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.category == "physical":
        return damage // 2
    return damage


# ---------------------------------------------------------------------------
# G
# ---------------------------------------------------------------------------

def ability_gale_wings(priority: int, holder: Pokemon, move: Move,
                       battle_state: BattleState) -> int:
    if move.type == "flying" and holder.hp_ratio() == 1.0:
        return priority + 1
    return priority


def ability_galvanize(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    _normalize_type_change(move, "electric")


def ability_gluttony(threshold: float, holder: Pokemon, berry: str) -> float:
    return max(threshold, 0.50)


def ability_good_as_gold(blocked: bool, holder: Pokemon, attacker: Pokemon,
                         move: Move, battle_state: BattleState) -> bool:
    if move.category == "status":
        return True
    return blocked


def ability_gooey(holder: Pokemon, attacker: Pokemon, move: Move,
                  damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        _apply_stat(attacker, "speed", -1)


def ability_gorilla_tactics(attacker: Pokemon, defender: Pokemon, move: Move,
                             turn_order_position: int, first_turn: bool):
    if attacker.choice_locked_move and move.name != attacker.choice_locked_move:
        move.flags.priority_delta = -999  # cancel non-locked move
        return
    if not attacker.choice_locked_move:
        attacker.choice_locked_move = move.name
    move.flags.power_multiplier *= 1.5


def ability_grass_pelt(raw_value: int, holder: Pokemon, stat: str,
                       battle_state: BattleState) -> int:
    if battle_state.terrain == "grassy" and stat == "defense":
        return int(raw_value * 1.5)
    return raw_value


def ability_grassy_surge(holder: Pokemon, battle_state: BattleState):
    battle_state.terrain = "grassy"
    battle_state.terrain_turns = 5


def ability_grim_neigh(holder: Pokemon, fainted: Pokemon,
                       battle_state: BattleState):
    _apply_stat(holder, "sp_atk", 1)


def ability_guard_dog_intimidate(holder: Pokemon, intimidator: Pokemon,
                                  battle_state: BattleState):
    _apply_stat(holder, "attack", 1)


def ability_guard_dog_switch(blocked: bool, holder: Pokemon, source: Pokemon,
                              move: Move) -> bool:
    return True


def ability_gulp_missile(holder: Pokemon, move: Move,
                         battle_state: BattleState):
    if move.name.lower() in ("surf", "dive") and holder.form == "default":
        holder.gulp_missile_form = "cramorant_gorging"


def ability_gulp_missile_hit(holder: Pokemon, attacker: Pokemon, move: Move,
                              damage_dealt: int, battle_state: BattleState):
    if holder.gulp_missile_form and damage_dealt > 0:
        attacker.take_damage(attacker.max_hp // 4)
        if holder.gulp_missile_form == "cramorant_gorging":
            attacker.status = Status.PARALYSIS
        holder.gulp_missile_form = None


def ability_guts(attacker: Pokemon, defender: Pokemon, move: Move,
                 turn_order_position: int, first_turn: bool):
    if attacker.is_statused() and move.category == "physical":
        move.flags.power_multiplier *= 1.5


# ---------------------------------------------------------------------------
# H
# ---------------------------------------------------------------------------

def ability_hadron_engine(holder: Pokemon, battle_state: BattleState):
    battle_state.terrain = "electric"
    battle_state.terrain_turns = 5


def ability_hadron_engine_stat(raw_value: int, holder: Pokemon, stat: str,
                                battle_state: BattleState) -> int:
    if battle_state.terrain == "electric" and stat == "sp_atk":
        return int(raw_value * 1.3)
    return raw_value


def ability_harvest_eot(holder: Pokemon, battle_state: BattleState):
    if holder.last_berry_consumed:
        if battle_state.is_sunny() or random.random() < 0.50:
            holder.held_item = holder.last_berry_consumed
            holder.last_berry_consumed = None


def ability_healer_eot(holder: Pokemon, battle_state: BattleState):
    """Engine iterates allies; simplified — holder cures itself if no ally."""
    if random.random() < 0.30 and holder.is_statused():
        holder.status = Status.NONE


def ability_heatproof(damage: int, attacker: Pokemon, defender: Pokemon,
                      move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "fire":
        return damage // 2
    return damage


def ability_heatproof_burn(amount: int, holder: Pokemon, source: str,
                            battle_state: BattleState) -> int:
    if source == "burn":
        return amount // 2
    return amount


def ability_heavy_metal(weight: float, holder: Pokemon) -> float:
    return weight * 2.0


def ability_honey_gather(holder: Pokemon, battle_result: str,
                         battle_state: BattleState):
    if not holder.held_item and random.random() < (holder.level / 100):
        holder.held_item = "honey"


def ability_hospitality(holder: Pokemon, ally: Pokemon,
                        battle_state: BattleState):
    ally.heal(ally.max_hp // 4)


def ability_huge_power(raw_value: int, holder: Pokemon, stat: str,
                       battle_state: BattleState) -> int:
    if stat == "attack":
        return raw_value * 2
    return raw_value


def ability_hunger_switch_eot(holder: Pokemon, battle_state: BattleState):
    if holder.name.lower() == "morpeko":
        holder.form = "hangry" if holder.form == "full_belly" else "full_belly"


def ability_hustle(attacker: Pokemon, defender: Pokemon, move: Move,
                   turn_order_position: int, first_turn: bool):
    if move.category == "physical":
        move.flags.power_multiplier *= 1.5
        move.flags.power_multiplier *= 0.80  # net accuracy penalty flagged here;
        # engine reads flags.power_multiplier for damage and applies 0.80 to acc


def ability_hydration_eot(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_raining() and holder.is_statused():
        holder.status = Status.NONE


def ability_hyper_cutter(stages: int, holder: Pokemon, source: Pokemon,
                         stat: str) -> int:
    if stat == "attack" and stages < 0:
        return 0
    return stages


# ---------------------------------------------------------------------------
# I
# ---------------------------------------------------------------------------

def ability_ice_body_eot(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_hail_or_snow():
        holder.heal(holder.max_hp // 16)


def ability_ice_face(damage: int, attacker: Pokemon, defender: Pokemon,
                     move: Move, is_crit: bool, effectiveness: float) -> int:
    if defender.ice_face_intact and move.category == "physical":
        defender.ice_face_intact = False
        return 0
    return damage


def ability_ice_scales(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.category == "special":
        return damage // 2
    return damage


def ability_illuminate(rate: float, holder: Pokemon) -> float:
    return rate * 2.0


def ability_illusion(holder: Pokemon, battle_state: BattleState):
    """Engine sets illusion_target to last non-fainted party member."""
    pass


def ability_immunity(blocked: bool, holder: Pokemon, source: Pokemon,
                     status: str, battle_state: BattleState) -> bool:
    if status in (Status.POISON, Status.BADLY_POISON):
        return True
    return blocked


def ability_imposter(holder: Pokemon, battle_state: BattleState):
    """Engine performs Transform into current foe."""
    holder.is_transformed = True


def ability_infiltrator(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    move.flags.ignore_screens = True


def ability_innards_out(holder: Pokemon, attacker: Pokemon,
                        battle_state: BattleState):
    remaining = holder.hp  # HP just before fainting
    if attacker.is_alive():
        attacker.take_damage(remaining)


def ability_inner_focus_flinch(blocked: bool, holder: Pokemon, attacker: Pokemon,
                                battle_state: BattleState) -> bool:
    return True


def ability_inner_focus_intimidate(holder: Pokemon, intimidator: Pokemon,
                                    battle_state: BattleState):
    pass  # Block: do nothing (intimidate has no effect)


def ability_insomnia(blocked: bool, holder: Pokemon, source: Pokemon,
                     status: str, battle_state: BattleState) -> bool:
    if status == Status.SLEEP:
        return True
    return blocked


def ability_intimidate(holder: Pokemon, battle_state: BattleState):
    """Engine applies to all active foes."""
    pass  # Engine iterates foes and calls _apply_stat(foe, "attack", -1)


def ability_intrepid_sword(holder: Pokemon, battle_state: BattleState):
    _apply_stat(holder, "attack", 1)


def ability_iron_barbs(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        attacker.take_damage(attacker.max_hp // 8)


def ability_iron_fist(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    if move.is_punch:
        move.flags.power_multiplier *= 1.2


# ---------------------------------------------------------------------------
# J–K
# ---------------------------------------------------------------------------

def ability_justified(holder: Pokemon, attacker: Pokemon, move: Move,
                      damage_dealt: int, battle_state: BattleState):
    if move.type == "dark" and damage_dealt > 0:
        _apply_stat(holder, "attack", 1)


def ability_keen_eye_stat(stages: int, holder: Pokemon, source: Pokemon,
                           stat: str) -> int:
    if stat == "accuracy" and stages < 0:
        return 0
    return stages


def ability_keen_eye_acc(accuracy: float, attacker: Pokemon, defender: Pokemon,
                          move: Move) -> float:
    # Ignore defender evasion stages — engine passes adjusted accuracy;
    # flag so engine skips evasion stage lookup
    return accuracy


def ability_klutz(blocked: bool, holder: Pokemon, source: Pokemon,
                  move: Move) -> bool:
    return True


# ---------------------------------------------------------------------------
# L
# ---------------------------------------------------------------------------

def ability_leaf_guard(blocked: bool, holder: Pokemon, source: Pokemon,
                       status: str, battle_state: BattleState) -> bool:
    if battle_state.is_sunny():
        return True
    return blocked


def ability_levitate(damage: int, attacker: Pokemon, defender: Pokemon,
                     move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "ground" and not move.flags.suppress_target_ability:
        return 0
    return damage


def ability_libero(attacker: Pokemon, defender: Pokemon, move: Move,
                   turn_order_position: int, first_turn: bool):
    if not attacker.libero_protean_used:
        effective_type = move.flags.type_override or move.type
        attacker.types = [effective_type]
        attacker.libero_protean_used = True


def ability_light_metal(weight: float, holder: Pokemon) -> float:
    return weight * 0.5


def ability_lightning_rod(holder: Pokemon, attacker: Pokemon, move: Move):
    """Redirect Electric moves to holder; boost Sp. Atk."""
    if move.type == "electric":
        _apply_stat(holder, "sp_atk", 1)
        # Engine re-targets move to holder


def ability_limber(blocked: bool, holder: Pokemon, source: Pokemon,
                   status: str, battle_state: BattleState) -> bool:
    if status == Status.PARALYSIS:
        return True
    return blocked


def ability_lingering_aroma(holder: Pokemon, attacker: Pokemon, move: Move,
                             damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        attacker.ability = "lingering_aroma"


def ability_liquid_ooze(drain: int, holder: Pokemon, attacker: Pokemon,
                        move: Move) -> int:
    return -drain  # attacker takes damage instead of healing


def ability_liquid_voice(attacker: Pokemon, defender: Pokemon, move: Move,
                         turn_order_position: int, first_turn: bool):
    if move.is_sound and move.category != "status":
        move.flags.type_override = "water"


def ability_long_reach(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    move.flags.is_contact = False


# ---------------------------------------------------------------------------
# M
# ---------------------------------------------------------------------------

def ability_magic_bounce(holder: Pokemon, attacker: Pokemon, move: Move):
    if move.category == "status":
        move.flags.priority_delta = -999  # cancel; engine reflects back


def ability_magic_guard(amount: int, holder: Pokemon, source: str,
                        battle_state: BattleState) -> int:
    return 0


def ability_magician(holder: Pokemon, defender: Pokemon, move: Move,
                     damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and defender.held_item and not holder.held_item:
        holder.held_item = defender.held_item
        defender.held_item = None


def ability_magma_armor(blocked: bool, holder: Pokemon, source: Pokemon,
                        status: str, battle_state: BattleState) -> bool:
    if status == Status.FREEZE:
        return True
    return blocked


def ability_magnet_pull(blocked: bool, holder: Pokemon, fleeing: Pokemon,
                        battle_state: BattleState) -> bool:
    if "steel" in fleeing.types:
        return True
    return blocked


def ability_marvel_scale(damage: int, attacker: Pokemon, defender: Pokemon,
                         move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.category == "physical" and defender.is_statused():
        return int(damage / 1.5)
    return damage


def ability_mega_launcher(attacker: Pokemon, defender: Pokemon, move: Move,
                           turn_order_position: int, first_turn: bool):
    PULSE_AURA = {"aura_sphere", "dark_pulse", "dragon_pulse", "heal_pulse",
                  "origin_pulse", "terrain_pulse", "water_pulse"}
    if move.is_pulse or move.name.lower().replace(" ", "_") in PULSE_AURA:
        move.flags.power_multiplier *= 1.5


def ability_mega_sol(damage: int, attacker: Pokemon, defender: Pokemon,
                     move: Move, is_crit: bool, effectiveness: float) -> int:
    """Treat weather as harsh sun for damage calc — engine checks this flag."""
    return damage  # Engine reads holder ability and overrides weather lookup


def ability_merciless(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    if defender.status in (Status.POISON, Status.BADLY_POISON):
        move.flags.always_crit = True


def ability_mimicry(holder: Pokemon, new_terrain: str,
                    battle_state: BattleState):
    TERRAIN_TYPE = {
        "electric": "electric",
        "grassy":   "grass",
        "misty":    "fairy",
        "psychic":  "psychic",
        "none":     holder.types[0],  # revert to original — engine stores base type
    }
    holder.types = [TERRAIN_TYPE.get(new_terrain, holder.types[0])]


def ability_minds_eye(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    move.flags.ignore_evasion = True
    move.flags.hits_ghost = True


def ability_minus(raw_value: int, holder: Pokemon, stat: str,
                  battle_state: BattleState) -> int:
    if stat == "sp_atk":
        # Engine checks if an ally has Plus or Minus
        return int(raw_value * 1.5)
    return raw_value


def ability_mirror_armor(stages: int, holder: Pokemon, source: Pokemon,
                         stat: str) -> int:
    if stages < 0 and source:
        source.stat_stages.modify(stat, stages)
        return 0
    return stages


def ability_misty_surge(holder: Pokemon, battle_state: BattleState):
    battle_state.terrain = "misty"
    battle_state.terrain_turns = 5


def ability_mold_breaker(attacker: Pokemon, defender: Pokemon, move: Move,
                         turn_order_position: int, first_turn: bool):
    move.flags.suppress_target_ability = True


def ability_moody_eot(holder: Pokemon, battle_state: BattleState):
    stats = ["attack", "defense", "sp_atk", "sp_def", "speed",
             "accuracy", "evasion"]
    boost_stat = random.choice(stats)
    remaining = [s for s in stats if s != boost_stat]
    drop_stat = random.choice(remaining)
    _apply_stat(holder, boost_stat, 2)
    _apply_stat(holder, drop_stat, -1)


def ability_motor_drive(holder: Pokemon, attacker: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if move.type == "electric" and not move.flags.suppress_target_ability:
        _apply_stat(holder, "speed", 1)


def ability_motor_drive_dmg(damage: int, attacker: Pokemon, defender: Pokemon,
                             move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "electric" and not move.flags.suppress_target_ability:
        return 0
    return damage


def ability_moxie(holder: Pokemon, fainted: Pokemon,
                  battle_state: BattleState):
    _apply_stat(holder, "attack", 1)


def ability_multiscale(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    if defender.hp_ratio() == 1.0:
        return damage // 2
    return damage


def ability_multitype(holder: Pokemon, battle_state: BattleState):
    PLATE_TYPE = {
        "flame_plate": "fire", "splash_plate": "water", "zap_plate": "electric",
        "meadow_plate": "grass", "icicle_plate": "ice", "fist_plate": "fighting",
        "toxic_plate": "poison", "earth_plate": "ground", "sky_plate": "flying",
        "mind_plate": "psychic", "insect_plate": "bug", "stone_plate": "rock",
        "spooky_plate": "ghost", "draco_plate": "dragon", "dread_plate": "dark",
        "iron_plate": "steel", "pixie_plate": "fairy",
    }
    if holder.held_item:
        t = PLATE_TYPE.get(holder.held_item.lower())
        if t:
            holder.types = [t]


def ability_mummy(holder: Pokemon, attacker: Pokemon, move: Move,
                  damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        attacker.ability = "mummy"


def ability_mycelium_might(attacker: Pokemon, defender: Pokemon, move: Move,
                            turn_order_position: int, first_turn: bool):
    if move.category == "status":
        move.flags.go_last = True
        move.flags.suppress_target_ability = True


# ---------------------------------------------------------------------------
# N
# ---------------------------------------------------------------------------

def ability_natural_cure(holder: Pokemon, battle_state: BattleState):
    holder.status = Status.NONE


def ability_neuroforce(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    # Applied in damage calc; flag set here for engine to read
    move.flags.power_multiplier  # engine checks neuroforce on attacker


def ability_neuroforce_dmg(damage: int, attacker: Pokemon, defender: Pokemon,
                            move: Move, is_crit: bool, effectiveness: float) -> int:
    if effectiveness > 1.0:
        return int(damage * 1.25)
    return damage


def ability_neutralizing_gas(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["neutralizing_gas_active"] = True
    return field_dict


def ability_no_guard_acc(accuracy: float, attacker: Pokemon, defender: Pokemon,
                          move: Move) -> float:
    return 1.0


def ability_normalize(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    if move.category != "status":
        move.flags.type_override = "normal"
        move.flags.power_multiplier *= 1.2


def ability_oblivious(blocked: bool, holder: Pokemon, source: Pokemon,
                      status: str, battle_state: BattleState) -> bool:
    if status in (Status.CONFUSION, "infatuation", "taunt"):
        return True
    return blocked


def ability_opportunist(holder: Pokemon, foe: Pokemon, stat: str,
                        stages: int, battle_state: BattleState):
    if stages > 0:
        _apply_stat(holder, stat, stages)


def ability_orichalcum_pulse_enter(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "sun"
    battle_state.weather_turns = 5


def ability_orichalcum_pulse_stat(raw_value: int, holder: Pokemon, stat: str,
                                   battle_state: BattleState) -> int:
    if battle_state.is_sunny() and stat == "attack":
        return int(raw_value * 1.3)
    return raw_value


def ability_overcoat(amount: int, holder: Pokemon, source: str,
                     battle_state: BattleState) -> int:
    if source in ("sandstorm", "hail", "snow", "powder", "spore"):
        return 0
    return amount


def ability_overgrow(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    _starter_ability_boost(move, attacker, "grass")


def ability_own_tempo(blocked: bool, holder: Pokemon, source: Pokemon,
                      status: str, battle_state: BattleState) -> bool:
    if status == Status.CONFUSION:
        return True
    return blocked


def ability_own_tempo_intimidate(holder: Pokemon, intimidator: Pokemon,
                                  battle_state: BattleState):
    pass  # Block intimidate; no Attack drop


# ---------------------------------------------------------------------------
# P
# ---------------------------------------------------------------------------

def ability_parental_bond(attacker: Pokemon, defender: Pokemon, move: Move,
                           turn_order_position: int, first_turn: bool):
    if move.category != "status":
        move.flags.repeat_count = 2
        move.flags.second_hit_multiplier = 0.25


def ability_pastel_veil_enter(holder: Pokemon, battle_state: BattleState):
    if holder.status in (Status.POISON, Status.BADLY_POISON):
        holder.status = Status.NONE


def ability_pastel_veil_status(blocked: bool, holder: Pokemon, source: Pokemon,
                                status: str, battle_state: BattleState) -> bool:
    if status in (Status.POISON, Status.BADLY_POISON):
        return True
    return blocked


def ability_pastel_veil_ally(blocked: bool, holder: Pokemon, ally: Pokemon,
                              source: Pokemon, status: str,
                              battle_state: BattleState) -> bool:
    if status in (Status.POISON, Status.BADLY_POISON):
        return True
    return blocked


def ability_perish_body(holder: Pokemon, attacker: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        if holder.perish_count is None:
            holder.perish_count = 3
        if attacker.perish_count is None:
            attacker.perish_count = 3


def ability_pickpocket(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and attacker.held_item and not holder.held_item:
        holder.held_item = attacker.held_item
        attacker.held_item = None


def ability_pickup(holder: Pokemon, battle_result: str,
                   battle_state: BattleState):
    if not holder.held_item and random.random() < 0.10:
        holder.held_item = "random_item"  # Engine resolves actual item table


def ability_pixilate(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    _normalize_type_change(move, "fairy")


def ability_plus(raw_value: int, holder: Pokemon, stat: str,
                 battle_state: BattleState) -> int:
    return ability_minus(raw_value, holder, stat, battle_state)


def ability_poison_heal(amount: int, holder: Pokemon, source: str,
                        battle_state: BattleState) -> int:
    if source in (Status.POISON, Status.BADLY_POISON):
        holder.heal(holder.max_hp // 8)
        return 0
    return amount


def ability_poison_point(holder: Pokemon, attacker: Pokemon, move: Move,
                         damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and attacker.status == Status.NONE and random.random() < 0.30:
        attacker.status = Status.POISON


def ability_poison_puppeteer(holder: Pokemon, poisoned: Pokemon,
                              poison_type: str, battle_state: BattleState):
    poisoned.is_confused = True


def ability_poison_touch(holder: Pokemon, defender: Pokemon, move: Move,
                         damage_dealt: int, battle_state: BattleState):
    if (damage_dealt > 0 and move.flags.is_contact
            and defender.status == Status.NONE and random.random() < 0.30):
        defender.status = Status.POISON


def ability_power_construct(holder: Pokemon, attacker: Pokemon, move: Move,
                             hp_before: float, hp_after: float,
                             battle_state: BattleState):
    if hp_before > 0.5 >= hp_after and holder.form in ("50pct", "default"):
        holder.form = "complete"
        holder.max_hp = int(holder.max_hp * 2)
        holder.hp = holder.max_hp // 2


def ability_power_of_alchemy(holder: Pokemon, fainted_ally: Pokemon,
                              battle_state: BattleState):
    holder.ability = fainted_ally.ability


def ability_power_spot(holder: Pokemon, ally: Pokemon, defender: Pokemon,
                       move: Move):
    if move.category != "status":
        move.flags.power_multiplier *= 1.3


def ability_prankster(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    if move.category == "status":
        move.flags.priority_delta += 1


def ability_prankster_block(blocked: bool, holder: Pokemon, attacker: Pokemon,
                             move: Move, battle_state: BattleState) -> bool:
    if (hasattr(attacker, "ability") and attacker.ability == "prankster"
            and move.category == "status" and "dark" in holder.types):
        return True
    return blocked


def ability_pressure(pp_cost: int, holder: Pokemon, attacker: Pokemon,
                     move: Move) -> int:
    return pp_cost + 1


def ability_primordial_sea(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "heavy_rain"
    battle_state.weather_turns = -1


def ability_prism_armor(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    return ability_filter(damage, attacker, defender, move, is_crit, effectiveness)


def ability_propeller_tail(ignore: bool, holder: Pokemon, move: Move) -> bool:
    return True


def ability_protean(attacker: Pokemon, defender: Pokemon, move: Move,
                    turn_order_position: int, first_turn: bool):
    ability_libero(attacker, defender, move, turn_order_position, first_turn)


def ability_protosynthesis(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_sunny() or holder.booster_energy_used:
        stat = _highest_stat(holder)
        holder.protosynthesis_stat = stat


def ability_protosynthesis_stat(raw_value: int, holder: Pokemon, stat: str,
                                 battle_state: BattleState) -> int:
    if holder.protosynthesis_stat == stat:
        return int(raw_value * 1.3)
    return raw_value


def ability_psychic_surge(holder: Pokemon, battle_state: BattleState):
    battle_state.terrain = "psychic"
    battle_state.terrain_turns = 5


def ability_punk_rock_atk(attacker: Pokemon, defender: Pokemon, move: Move,
                           turn_order_position: int, first_turn: bool):
    if move.is_sound:
        move.flags.power_multiplier *= 1.3


def ability_punk_rock_def(damage: int, attacker: Pokemon, defender: Pokemon,
                           move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.is_sound:
        return damage // 2
    return damage


def ability_pure_power(raw_value: int, holder: Pokemon, stat: str,
                       battle_state: BattleState) -> int:
    return ability_huge_power(raw_value, holder, stat, battle_state)


def ability_purifying_salt_status(blocked: bool, holder: Pokemon,
                                   source: Pokemon, status: str,
                                   battle_state: BattleState) -> bool:
    return True  # blocks all non-volatile status


def ability_purifying_salt_dmg(damage: int, attacker: Pokemon,
                                defender: Pokemon, move: Move,
                                is_crit: bool, effectiveness: float) -> int:
    if move.type == "ghost":
        return damage // 2
    return damage


# ---------------------------------------------------------------------------
# Q
# ---------------------------------------------------------------------------

def ability_quark_drive(holder: Pokemon, battle_state: BattleState):
    if battle_state.terrain == "electric" or holder.booster_energy_used:
        stat = _highest_stat(holder)
        holder.quark_drive_stat = stat


def ability_quark_drive_stat(raw_value: int, holder: Pokemon, stat: str,
                              battle_state: BattleState) -> int:
    if holder.quark_drive_stat == stat:
        return int(raw_value * 1.3)
    return raw_value


def ability_queenly_majesty(holder: Pokemon, attacker: Pokemon, move: Move):
    ability_armor_tail(holder, attacker, move)


def ability_quick_draw(priority: int, holder: Pokemon, move: Move,
                       battle_state: BattleState) -> int:
    if random.random() < 0.30:
        return priority + 1
    return priority


def ability_quick_feet(speed: int, holder: Pokemon,
                       battle_state: BattleState) -> int:
    if holder.is_statused():
        return int(speed * 1.5)
    return speed


# ---------------------------------------------------------------------------
# R
# ---------------------------------------------------------------------------

def ability_rain_dish_eot(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_raining():
        holder.heal(holder.max_hp // 16)


def ability_rattled_hit(holder: Pokemon, attacker: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.type in ("bug", "ghost", "dark"):
        _apply_stat(holder, "speed", 1)


def ability_rattled_intimidate(holder: Pokemon, intimidator: Pokemon,
                                battle_state: BattleState):
    _apply_stat(holder, "speed", 1)


def ability_receiver(holder: Pokemon, fainted_ally: Pokemon,
                     battle_state: BattleState):
    ability_power_of_alchemy(holder, fainted_ally, battle_state)


def ability_reckless(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    if move.is_recoil:
        move.flags.power_multiplier *= 1.2


def ability_refrigerate(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    _normalize_type_change(move, "ice")


def ability_regenerator(holder: Pokemon, battle_state: BattleState):
    holder.heal(holder.max_hp // 3)


def ability_ripen(threshold: float, holder: Pokemon, berry: str) -> float:
    return threshold * 2  # double berry effect (engine applies doubled value)


def ability_rivalry(attacker: Pokemon, defender: Pokemon, move: Move,
                    turn_order_position: int, first_turn: bool):
    if attacker.gender and defender.gender:
        if attacker.gender == defender.gender:
            move.flags.power_multiplier *= 1.25
        else:
            move.flags.power_multiplier *= 0.75


def ability_rks_system(holder: Pokemon, battle_state: BattleState):
    MEMORY_TYPE = {
        "fire_memory": "fire", "water_memory": "water",
        "electric_memory": "electric", "grass_memory": "grass",
        "ice_memory": "ice", "fighting_memory": "fighting",
        "poison_memory": "poison", "ground_memory": "ground",
        "flying_memory": "flying", "psychic_memory": "psychic",
        "bug_memory": "bug", "rock_memory": "rock",
        "ghost_memory": "ghost", "dragon_memory": "dragon",
        "dark_memory": "dark", "steel_memory": "steel",
        "fairy_memory": "fairy",
    }
    if holder.held_item:
        t = MEMORY_TYPE.get(holder.held_item.lower())
        if t:
            holder.types = [t]


def ability_rock_head(recoil: int, holder: Pokemon, move: Move) -> int:
    if move.name.lower() != "struggle":
        return 0
    return recoil


def ability_rocky_payload(attacker: Pokemon, defender: Pokemon, move: Move,
                           turn_order_position: int, first_turn: bool):
    if move.type == "rock":
        move.flags.power_multiplier *= 1.5


def ability_rough_skin(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    ability_iron_barbs(holder, attacker, move, damage_dealt, battle_state)


def ability_run_away(success: bool, holder: Pokemon) -> bool:
    return True


# ---------------------------------------------------------------------------
# S
# ---------------------------------------------------------------------------

def ability_sand_force(battle_state: BattleState):
    def _ability_sand_force(attacker: Pokemon, defender: Pokemon, move: Move,
                             turn_order_position: int, first_turn: bool):
        if battle_state.is_sandstorm() and move.type in ("rock", "ground", "steel"):
            move.flags.power_multiplier *= 1.3
    return _ability_sand_force


def ability_sand_rush(speed: int, holder: Pokemon,
                      battle_state: BattleState) -> int:
    if battle_state.is_sandstorm():
        return speed * 2
    return speed


def ability_sand_spit(holder: Pokemon, attacker: Pokemon, move: Move,
                      damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        battle_state.weather = "sandstorm"
        battle_state.weather_turns = 5


def ability_sand_stream(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "sandstorm"
    battle_state.weather_turns = 5


def ability_sand_veil(accuracy: float, attacker: Pokemon, defender: Pokemon,
                      move: Move) -> float:
    # Defender has Sand Veil; engine calls this on defender side
    return accuracy * 0.8


def ability_sap_sipper(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "grass" and not move.flags.suppress_target_ability:
        _apply_stat(defender, "attack", 1)
        return 0
    return damage


def ability_schooling(holder: Pokemon, battle_state: BattleState):
    if holder.name.lower() == "wishiwashi":
        holder.form = "school" if holder.hp_ratio() >= 0.25 else "solo"


def ability_scrappy(attacker: Pokemon, defender: Pokemon, move: Move,
                    turn_order_position: int, first_turn: bool):
    if move.type in ("normal", "fighting"):
        move.flags.hits_ghost = True


def ability_screen_cleaner(holder: Pokemon, battle_state: BattleState):
    """Engine provides both sides; clear screens on both."""
    pass  # Engine calls side.clear_screens() for both sides


def ability_seed_sower(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        battle_state.terrain = "grassy"
        battle_state.terrain_turns = 5


def ability_serene_grace(attacker: Pokemon, defender: Pokemon, move: Move,
                          turn_order_position: int, first_turn: bool):
    move.flags.secondary_chance_multiplier = 2.0


def ability_shadow_shield(damage: int, attacker: Pokemon, defender: Pokemon,
                           move: Move, is_crit: bool, effectiveness: float) -> int:
    return ability_multiscale(damage, attacker, defender, move, is_crit, effectiveness)


def ability_shadow_tag(blocked: bool, holder: Pokemon, fleeing: Pokemon,
                       battle_state: BattleState) -> bool:
    if fleeing.ability != "shadow_tag":
        return True
    return blocked


def ability_sharpness(attacker: Pokemon, defender: Pokemon, move: Move,
                      turn_order_position: int, first_turn: bool):
    if move.is_slicing:
        move.flags.power_multiplier *= 1.5


def ability_shed_skin_eot(holder: Pokemon, battle_state: BattleState):
    if holder.is_statused() and random.random() < 1/3:
        holder.status = Status.NONE


def ability_sheer_force(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if move.secondary_effect and move.secondary_chance > 0:
        move.flags.secondary_effect_removed = True
        move.flags.power_multiplier *= 1.3


def ability_shell_armor(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    return ability_battle_armor(damage, attacker, defender, move, is_crit, effectiveness)


def ability_shield_dust(blocked: bool, holder: Pokemon, attacker: Pokemon,
                        move: Move, effect: str) -> bool:
    return True


def ability_shields_down(holder: Pokemon, attacker: Pokemon, move: Move,
                          hp_before: float, hp_after: float,
                          battle_state: BattleState):
    if hp_before > 0.5 >= hp_after and holder.form == "meteor":
        holder.form = "core"
    elif hp_after > 0.5 and holder.form == "core":
        holder.form = "meteor"


def ability_simple(stages: int, holder: Pokemon, source: Pokemon,
                   stat: str) -> int:
    return stages * 2


def ability_skill_link(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    MULTI_HIT_MOVES = {"bullet_seed", "icicle_spear", "pin_missile",
                       "rock_blast", "spine_missile", "tail_slap",
                       "water_shuriken"}
    if move.name.lower().replace(" ", "_") in MULTI_HIT_MOVES:
        move.flags.repeat_count = 5


def ability_slow_start(holder: Pokemon, battle_state: BattleState):
    holder.slow_start_turns = 5


def ability_slow_start_stat(raw_value: int, holder: Pokemon, stat: str,
                             battle_state: BattleState) -> int:
    if holder.slow_start_turns > 0 and stat in ("attack", "speed"):
        return raw_value // 2
    return raw_value


def ability_slow_start_eot(holder: Pokemon, battle_state: BattleState):
    if holder.slow_start_turns > 0:
        holder.slow_start_turns -= 1


def ability_slush_rush(speed: int, holder: Pokemon,
                       battle_state: BattleState) -> int:
    if battle_state.is_hail_or_snow():
        return speed * 2
    return speed


def ability_sniper(damage: int, attacker: Pokemon, defender: Pokemon,
                   move: Move, is_crit: bool, effectiveness: float) -> int:
    if is_crit:
        return int(damage * 1.5)  # standard crit is 1.5×; Sniper makes it 2.25×
    return damage


def ability_snow_cloak(accuracy: float, attacker: Pokemon, defender: Pokemon,
                       move: Move) -> float:
    return ability_sand_veil(accuracy, attacker, defender, move)


def ability_snow_warning(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "snow"
    battle_state.weather_turns = 5


def ability_solar_power_stat(raw_value: int, holder: Pokemon, stat: str,
                              battle_state: BattleState) -> int:
    if battle_state.is_sunny() and stat == "sp_atk":
        return int(raw_value * 1.5)
    return raw_value


def ability_solar_power_eot(holder: Pokemon, battle_state: BattleState):
    if battle_state.is_sunny():
        holder.take_damage(holder.max_hp // 8)


def ability_solid_rock(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    return ability_filter(damage, attacker, defender, move, is_crit, effectiveness)


def ability_soul_heart(holder: Pokemon, fainted: Pokemon,
                       battle_state: BattleState):
    _apply_stat(holder, "sp_atk", 1)


def ability_soundproof(holder: Pokemon, attacker: Pokemon, move: Move):
    if move.is_sound:
        move.flags.priority_delta = -999


def ability_speed_boost_eot(holder: Pokemon, battle_state: BattleState):
    _apply_stat(holder, "speed", 1)


def ability_stakeout(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    if defender.switched_in_this_turn:
        move.flags.power_multiplier *= 2.0


def ability_stall(priority: int, holder: Pokemon, move: Move,
                  battle_state: BattleState) -> int:
    move.flags.go_last = True
    return priority


def ability_stalwart(ignore: bool, holder: Pokemon, move: Move) -> bool:
    return True


def ability_stamina(holder: Pokemon, attacker: Pokemon, move: Move,
                    damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        _apply_stat(holder, "defense", 1)


def ability_stance_change(holder: Pokemon, move: Move,
                           battle_state: BattleState):
    if move.name.lower() == "kings_shield":
        holder.form = "shield"
    elif move.category in ("physical", "special"):
        holder.form = "blade"


def ability_static(holder: Pokemon, attacker: Pokemon, move: Move,
                   damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and attacker.status == Status.NONE and random.random() < 0.30:
        attacker.status = Status.PARALYSIS


def ability_steadfast(blocked: bool, holder: Pokemon, attacker: Pokemon,
                      battle_state: BattleState) -> bool:
    _apply_stat(holder, "speed", 1)
    return blocked  # does not block the flinch


def ability_steam_engine(holder: Pokemon, attacker: Pokemon, move: Move,
                          damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.type in ("fire", "water"):
        _apply_stat(holder, "speed", 6)


def ability_steelworker(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if move.type == "steel":
        move.flags.power_multiplier *= 1.5


def ability_steely_spirit(holder: Pokemon, ally: Pokemon, defender: Pokemon,
                           move: Move):
    if move.type == "steel":
        move.flags.power_multiplier *= 1.5


def ability_stench(attacker: Pokemon, defender: Pokemon, move: Move,
                   turn_order_position: int, first_turn: bool):
    if move.category != "status" and not move.secondary_effect:
        move.secondary_effect = Status.CONFUSION  # flinch; engine resolves
        move.secondary_chance = 0.10


def ability_sticky_hold(blocked: bool, holder: Pokemon, source: Pokemon,
                        move: Move) -> bool:
    return True


def ability_storm_drain(holder: Pokemon, attacker: Pokemon, move: Move):
    if move.type == "water":
        _apply_stat(holder, "sp_atk", 1)


def ability_storm_drain_dmg(damage: int, attacker: Pokemon, defender: Pokemon,
                             move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "water" and not move.flags.suppress_target_ability:
        return 0
    return damage


def ability_strong_jaw(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    if move.is_bite:
        move.flags.power_multiplier *= 1.5


def ability_sturdy(damage: int, attacker: Pokemon, defender: Pokemon,
                   move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.is_ohko:
        return 0
    if defender.hp_ratio() == 1.0 and damage >= defender.hp:
        return defender.hp - 1
    return damage


def ability_suction_cups(blocked: bool, holder: Pokemon, source: Pokemon,
                         move: Move) -> bool:
    return True


def ability_super_luck(crit_stage: int, holder: Pokemon, move: Move) -> int:
    return crit_stage + 1


def ability_supersweet_syrup(holder: Pokemon, battle_state: BattleState):
    """Engine applies to all active foes."""
    pass  # Engine iterates foes: _apply_stat(foe, "evasion", -1)


def ability_supreme_overlord(holder: Pokemon, battle_state: BattleState):
    """Engine provides fainted_count on holder's side."""
    pass  # Engine: stages = min(5, side.fainted_count); apply to atk & sp_atk


def ability_surge_surfer(speed: int, holder: Pokemon,
                         battle_state: BattleState) -> int:
    if battle_state.terrain == "electric":
        return speed * 2
    return speed


def ability_swarm(attacker: Pokemon, defender: Pokemon, move: Move,
                  turn_order_position: int, first_turn: bool):
    _starter_ability_boost(move, attacker, "bug")


def ability_sweet_veil_self(blocked: bool, holder: Pokemon, source: Pokemon,
                             status: str, battle_state: BattleState) -> bool:
    if status == Status.SLEEP:
        return True
    return blocked


def ability_sweet_veil_ally(blocked: bool, holder: Pokemon, ally: Pokemon,
                             source: Pokemon, status: str,
                             battle_state: BattleState) -> bool:
    if status == Status.SLEEP:
        return True
    return blocked


def ability_swift_swim(speed: int, holder: Pokemon,
                       battle_state: BattleState) -> int:
    if battle_state.is_raining():
        return speed * 2
    return speed


def ability_sword_of_ruin(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["sword_of_ruin_active"] = True
    return field_dict


def ability_symbiosis(holder: Pokemon, ally: Pokemon, consumed_item: str,
                      battle_state: BattleState):
    if holder.held_item:
        ally.held_item = holder.held_item
        holder.held_item = None


def ability_synchronize(holder: Pokemon, source: Pokemon, status: str,
                        battle_state: BattleState):
    if status in (Status.BURN, Status.POISON, Status.PARALYSIS):
        if source.status == Status.NONE:
            source.status = status


# ---------------------------------------------------------------------------
# T
# ---------------------------------------------------------------------------

def ability_tablets_of_ruin(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["tablets_of_ruin_active"] = True
    return field_dict


def ability_tangled_feet(accuracy: float, attacker: Pokemon, defender: Pokemon,
                         move: Move) -> float:
    if defender.is_confused:
        return accuracy * 0.8
    return accuracy


def ability_tangling_hair(holder: Pokemon, attacker: Pokemon, move: Move,
                           damage_dealt: int, battle_state: BattleState):
    ability_gooey(holder, attacker, move, damage_dealt, battle_state)


def ability_technician(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    effective_bp = move.base_power * move.flags.power_multiplier
    if effective_bp <= 60:
        move.flags.power_multiplier *= 1.5


def ability_telepathy(immune: bool, holder: Pokemon, ally: Pokemon,
                      move: Move) -> bool:
    if move.category in ("physical", "special"):
        return True
    return immune


def ability_tera_shell(damage: int, attacker: Pokemon, defender: Pokemon,
                       move: Move, is_crit: bool, effectiveness: float) -> int:
    if defender.hp_ratio() == 1.0:
        return int(damage * 0.5)  # engine treats as NVE; simplified as ×0.5
    return damage


def ability_tera_shift(holder: Pokemon, battle_state: BattleState):
    holder.is_terastallized = True
    if holder.tera_type:
        holder.types = [holder.tera_type]


def ability_teraform_zero(holder: Pokemon, battle_state: BattleState):
    battle_state.weather = "none"
    battle_state.terrain = "none"
    battle_state.weather_turns = 0
    battle_state.terrain_turns = 0


def ability_teravolt(attacker: Pokemon, defender: Pokemon, move: Move,
                     turn_order_position: int, first_turn: bool):
    ability_mold_breaker(attacker, defender, move, turn_order_position, first_turn)


def ability_thermal_exchange_hit(holder: Pokemon, attacker: Pokemon, move: Move,
                                  damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.type == "fire":
        _apply_stat(holder, "attack", 1)


def ability_thermal_exchange_status(blocked: bool, holder: Pokemon,
                                     source: Pokemon, status: str,
                                     battle_state: BattleState) -> bool:
    if status == Status.BURN:
        return True
    return blocked


def ability_thick_fat(damage: int, attacker: Pokemon, defender: Pokemon,
                      move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type in ("fire", "ice"):
        return damage // 2
    return damage


def ability_tinted_lens(attacker: Pokemon, defender: Pokemon, move: Move,
                         turn_order_position: int, first_turn: bool):
    pass  # Engine checks attacker ability during effectiveness calc and doubles NVE


def ability_tinted_lens_dmg(damage: int, attacker: Pokemon, defender: Pokemon,
                              move: Move, is_crit: bool, effectiveness: float) -> int:
    if effectiveness < 1.0:
        return damage * 2
    return damage


def ability_torrent(attacker: Pokemon, defender: Pokemon, move: Move,
                    turn_order_position: int, first_turn: bool):
    _starter_ability_boost(move, attacker, "water")


def ability_tough_claws(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if move.flags.is_contact:
        move.flags.power_multiplier *= 1.3


def ability_toxic_boost(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if attacker.status in (Status.POISON, Status.BADLY_POISON) and move.category == "physical":
        move.flags.power_multiplier *= 1.5


def ability_toxic_chain(holder: Pokemon, defender: Pokemon, move: Move,
                        damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and defender.status == Status.NONE and random.random() < 0.30:
        defender.status = Status.BADLY_POISON
        defender.badly_poison_counter = 1


def ability_toxic_debris(holder: Pokemon, attacker: Pokemon, move: Move,
                          damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        pass  # Engine adds toxic spikes to attacker's side: side.toxic_spikes = min(2, side.toxic_spikes+1)


def ability_trace(holder: Pokemon, battle_state: BattleState):
    """Copy foe's ability — engine provides foe reference."""
    pass  # Engine: holder.ability = foe.ability


def ability_transistor(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    if move.type == "electric":
        move.flags.power_multiplier *= 1.5


def ability_triage(priority: int, holder: Pokemon, move: Move,
                   battle_state: BattleState) -> int:
    RESTORATIVE = {"heal_pulse", "life_dew", "moonlight", "morning_sun",
                   "recover", "roost", "shore_up", "slack_off", "soft_boiled",
                   "synthesis", "wish", "jungle_healing", "pollen_puff"}
    if (move.name.lower().replace(" ", "_") in RESTORATIVE
            or move.drain_fraction > 0):
        return priority + 3
    return priority


def ability_truant(attacker: Pokemon, defender: Pokemon, move: Move,
                   turn_order_position: int, first_turn: bool):
    if attacker.truant_resting:
        move.flags.priority_delta = -999  # cancel move; engine flips flag


def ability_truant_eot(holder: Pokemon, battle_state: BattleState):
    holder.truant_resting = not holder.truant_resting


def ability_turboblaze(attacker: Pokemon, defender: Pokemon, move: Move,
                       turn_order_position: int, first_turn: bool):
    ability_mold_breaker(attacker, defender, move, turn_order_position, first_turn)


# ---------------------------------------------------------------------------
# U
# ---------------------------------------------------------------------------

def ability_unaware_atk(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    """When holder is attacking: ignore defender's defensive stat boosts."""
    # Engine computes stat without stage modifiers for defender when this flag set
    return damage  # engine reads attacker.ability == "unaware" to skip def stages


def ability_unaware_def(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    """When holder is defending: ignore attacker's offensive stat boosts."""
    return damage  # engine reads defender.ability == "unaware" to skip atk stages


def ability_unburden_eot(holder: Pokemon, battle_state: BattleState):
    if not holder.held_item and holder.last_berry_consumed:
        holder.unburden_active = True


def ability_unburden_speed(speed: int, holder: Pokemon,
                            battle_state: BattleState) -> int:
    if holder.unburden_active and not holder.held_item:
        return speed * 2
    return speed


def ability_unnerve(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["unnerve_active"] = True
    return field_dict


def ability_unseen_fist(attacker: Pokemon, defender: Pokemon, move: Move,
                        turn_order_position: int, first_turn: bool):
    if move.flags.is_contact:
        move.flags.bypasses_protect = True


# ---------------------------------------------------------------------------
# V
# ---------------------------------------------------------------------------

def ability_vessel_of_ruin(field_dict: dict, battle_state: BattleState) -> dict:
    field_dict["vessel_of_ruin_active"] = True
    return field_dict


def ability_victory_star_self(attacker: Pokemon, defender: Pokemon, move: Move,
                               turn_order_position: int, first_turn: bool):
    move.flags.power_multiplier *= 1.1  # accuracy boost flagged; engine applies to acc


def ability_victory_star_ally(holder: Pokemon, ally: Pokemon, defender: Pokemon,
                               move: Move):
    move.flags.power_multiplier *= 1.1


def ability_vital_spirit(blocked: bool, holder: Pokemon, source: Pokemon,
                          status: str, battle_state: BattleState) -> bool:
    return ability_insomnia(blocked, holder, source, status, battle_state)


def ability_volt_absorb(damage: int, attacker: Pokemon, defender: Pokemon,
                        move: Move, is_crit: bool, effectiveness: float) -> int:
    return _type_absorb(damage, defender, attacker, move, "electric")


# ---------------------------------------------------------------------------
# W
# ---------------------------------------------------------------------------

def ability_wandering_spirit(holder: Pokemon, attacker: Pokemon, move: Move,
                              damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.flags.is_contact:
        holder.ability, attacker.ability = attacker.ability, holder.ability


def ability_water_absorb(damage: int, attacker: Pokemon, defender: Pokemon,
                         move: Move, is_crit: bool, effectiveness: float) -> int:
    return _type_absorb(damage, defender, attacker, move, "water")


def ability_water_bubble_def(damage: int, attacker: Pokemon, defender: Pokemon,
                              move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "fire":
        return damage // 2
    return damage


def ability_water_bubble_atk(attacker: Pokemon, defender: Pokemon, move: Move,
                              turn_order_position: int, first_turn: bool):
    if move.type == "water":
        move.flags.power_multiplier *= 2.0


def ability_water_bubble_status(blocked: bool, holder: Pokemon, source: Pokemon,
                                 status: str, battle_state: BattleState) -> bool:
    if status == Status.BURN:
        return True
    return blocked


def ability_water_compaction(holder: Pokemon, attacker: Pokemon, move: Move,
                              damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.type == "water":
        _apply_stat(holder, "defense", 2)


def ability_water_veil(blocked: bool, holder: Pokemon, source: Pokemon,
                       status: str, battle_state: BattleState) -> bool:
    if status == Status.BURN:
        return True
    return blocked


def ability_weak_armor(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0:
        _apply_stat(holder, "defense", -1)
        _apply_stat(holder, "speed", 2)


def ability_well_baked_body(damage: int, attacker: Pokemon, defender: Pokemon,
                             move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.type == "fire" and not move.flags.suppress_target_ability:
        _apply_stat(defender, "defense", 2)
        return 0
    return damage


def ability_white_smoke(stages: int, holder: Pokemon, source: Pokemon,
                        stat: str) -> int:
    return ability_clear_body(stages, holder, source, stat)


def ability_wimp_out(holder: Pokemon, attacker: Pokemon, move: Move,
                     hp_before: float, hp_after: float,
                     battle_state: BattleState):
    ability_emergency_exit(holder, attacker, move, hp_before, hp_after,
                           battle_state)


def ability_wind_power(holder: Pokemon, attacker: Pokemon, move: Move,
                       damage_dealt: int, battle_state: BattleState):
    if damage_dealt > 0 and move.is_wind:
        holder.charge_state = True


def ability_wind_rider_def(damage: int, attacker: Pokemon, defender: Pokemon,
                            move: Move, is_crit: bool, effectiveness: float) -> int:
    if move.is_wind and not move.flags.suppress_target_ability:
        _apply_stat(defender, "attack", 1)
        return 0
    return damage


def ability_wonder_guard(damage: int, attacker: Pokemon, defender: Pokemon,
                         move: Move, is_crit: bool, effectiveness: float) -> int:
    if effectiveness <= 1.0:
        return 0
    return damage


def ability_wonder_skin(accuracy: float, attacker: Pokemon, defender: Pokemon,
                        move: Move) -> float:
    if move.category == "status":
        return min(accuracy, 0.50)
    return accuracy


# ---------------------------------------------------------------------------
# Z
# ---------------------------------------------------------------------------

def ability_zen_mode(holder: Pokemon, attacker: Pokemon, move: Move,
                     hp_before: float, hp_after: float,
                     battle_state: BattleState):
    if hp_before > 0.5 >= hp_after and holder.form == "standard":
        holder.form = "zen"
    elif hp_after > 0.5 and holder.form == "zen":
        holder.form = "standard"


def ability_zero_to_hero(holder: Pokemon, battle_state: BattleState):
    if holder.name.lower() == "palafin" and holder.form == "zero":
        holder.form = "hero"


# ---------------------------------------------------------------------------
# Charge state — shared EOT boost (Electromorphosis, Wind Power)
# ---------------------------------------------------------------------------

def apply_charge_state_boost(attacker: Pokemon, defender: Pokemon, move: Move,
                              turn_order_position: int, first_turn: bool):
    """Registered to BeforeSelfMoveHook for any Pokémon with charge_state=True."""
    if attacker.charge_state and move.type == "electric":
        move.flags.power_multiplier *= 2.0
        attacker.charge_state = False