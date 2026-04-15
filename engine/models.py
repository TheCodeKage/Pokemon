"""
Data models assumed by ability_functions.py.

Design decisions:
  - Pokemon      : central mutable object; ability functions read/write it directly.
  - Move         : carries flags that ability functions set before damage calc.
                   Flags are reset each time the move is used.
  - BattleState  : read-only snapshot of field conditions queried by functions.
  - Side         : one per player; holds entry hazards and screen state.
  - StatStages   : clamped [-6, +6] container; ability functions call modify().
  - Status       : simple string enum-style constants defined at module level.
  - Types        : string constants; moves and pokemon carry lists of them.

Stat names (used as string keys throughout):
    "attack", "defense", "sp_atk", "sp_def", "speed", "accuracy", "evasion"

Weather names:
    "none", "rain", "sun", "sandstorm", "hail", "snow", "heavy_rain",
    "harsh_sun", "strong_winds"

Terrain names:
    "none", "electric", "grassy", "misty", "psychic"

Status constants (Status.*):
    NONE, BURN, FREEZE, PARALYSIS, POISON, BADLY_POISON, SLEEP, CONFUSION
    (confusion is tracked separately on Pokemon.is_confused since it is
     volatile, but functions check Status.CONFUSION for symmetry)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

class Status:
    NONE         = "none"
    BURN         = "burn"
    FREEZE       = "freeze"
    PARALYSIS    = "paralysis"
    POISON       = "poison"
    BADLY_POISON = "badly_poison"
    SLEEP        = "sleep"
    CONFUSION    = "confusion"   # volatile; stored separately on Pokemon


# ---------------------------------------------------------------------------
# Move flags  (set by ability functions in BeforeSelfMoveHook)
# ---------------------------------------------------------------------------

@dataclass
class MoveFlags:
    """Mutable flags attached to a move instance for a single use."""
    is_contact:           bool = True
    bypasses_protect:     bool = False
    bypasses_ability:     bool = False   # Mold Breaker family
    go_last:              bool = False   # Stall / Mycelium Might
    force_last_in_tier:   bool = False   # Mycelium Might (status moves)
    ignore_evasion:       bool = False   # Mind's Eye / No Guard
    secondary_effect_removed: bool = False  # Sheer Force
    secondary_chance_multiplier: float = 1.0  # Serene Grace
    power_multiplier:     float = 1.0
    type_override:        Optional[str] = None   # Aerilate family / Normalize
    priority_delta:       int = 0               # Prankster / Triage
    hits_ghost:           bool = False           # Scrappy / Mind's Eye
    repeat_count:         int = 1               # Parental Bond (2), Skill Link
    second_hit_multiplier: float = 1.0          # Parental Bond second hit ×0.25
    ignore_screens:       bool = False          # Infiltrator
    suppress_target_ability: bool = False       # Mold Breaker family
    always_crit:          bool = False          # Merciless


@dataclass
class Move:
    name:          str
    type:          str
    category:      str          # "physical", "special", "status"
    base_power:    int
    accuracy:      float        # 0.0–1.0; None = always hits
    pp:            int
    priority:      int = 0
    is_sound:      bool = False
    is_punch:      bool = False
    is_bite:       bool = False
    is_pulse:      bool = False
    is_ball:       bool = False
    is_bomb:       bool = False
    is_slicing:    bool = False
    is_wind:       bool = False
    is_dance:      bool = False
    is_recoil:     bool = False
    recoil_fraction: float = 0.0  # e.g. 0.33 for 1/3 recoil
    drain_fraction:  float = 0.0  # e.g. 0.5 for draining moves
    secondary_effect: Optional[str] = None      # e.g. "burn", "paralysis"
    secondary_chance: float = 0.0
    is_ohko:       bool = False
    flags:         MoveFlags = field(default_factory=MoveFlags)

    def reset_flags(self):
        self.flags = MoveFlags(is_contact=(self.category == "physical"))


# ---------------------------------------------------------------------------
# Stat stages
# ---------------------------------------------------------------------------

@dataclass
class StatStages:
    attack:   int = 0
    defense:  int = 0
    sp_atk:   int = 0
    sp_def:   int = 0
    speed:    int = 0
    accuracy: int = 0
    evasion:  int = 0

    _STAT_NAMES = ("attack", "defense", "sp_atk", "sp_def",
                   "speed", "accuracy", "evasion")

    def modify(self, stat: str, delta: int) -> int:
        """Apply delta, clamp to [-6, +6]. Returns actual change applied."""
        current = getattr(self, stat)
        new = max(-6, min(6, current + delta))
        setattr(self, stat, new)
        return new - current

    def reset(self):
        for s in self._STAT_NAMES:
            setattr(self, s, 0)

    def get(self, stat: str) -> int:
        return getattr(self, stat)


# ---------------------------------------------------------------------------
# Pokemon
# ---------------------------------------------------------------------------

@dataclass
class Pokemon:
    name:           str
    types:          list[str]               # 1 or 2 type strings
    ability:        str
    base_stats:     dict[str, int]          # {"attack": 100, ...}
    level:          int = 50
    hp:             int = 100
    max_hp:         int = 100
    status:         str = Status.NONE
    is_confused:    bool = False
    is_infatuated:  bool = False
    is_flinched:    bool = False
    stat_stages:    StatStages = field(default_factory=StatStages)
    held_item:      Optional[str] = None
    gender:         Optional[str] = None    # "male", "female", None
    weight:         float = 50.0            # kg
    is_grounded:    bool = True             # False = Levitate/Flying/Air Balloon

    # Volatile battle state
    sleep_turns_remaining:  int = 0
    badly_poison_counter:   int = 0
    perish_count:           Optional[int] = None   # None = not active
    choice_locked_move:     Optional[str] = None   # Gorilla Tactics / Choice items
    flash_fire_active:      bool = False
    charge_state:           bool = False    # Electromorphosis / Wind Power
    slow_start_turns:       int = 0
    truant_resting:         bool = False    # alternates each turn
    cud_chew_berry:         Optional[str] = None   # berry to re-consume at EOT
    last_berry_consumed:    Optional[str] = None
    illusion_target:        Optional["Pokemon"] = None  # Illusion disguise
    is_transformed:         bool = False
    transformed_into:       Optional["Pokemon"] = None
    unburden_active:        bool = False    # Unburden triggered
    disguise_intact:        bool = True     # Disguise / Ice Face
    ice_face_intact:        bool = True
    gulp_missile_form:      Optional[str] = None  # "pikachu" / "arrokuda" forms
    protosynthesis_stat:    Optional[str] = None  # which stat is boosted
    quark_drive_stat:       Optional[str] = None
    commander_active:       bool = False
    form:                   str = "default"
    tera_type:              Optional[str] = None
    is_terastallized:       bool = False
    booster_energy_used:    bool = False

    # Turn-scoped flags (reset each turn by engine)
    moved_this_turn:        bool = False
    switched_in_this_turn:  bool = False
    took_damage_this_turn:  bool = False
    libero_protean_used:    bool = False    # once per switch-in

    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)
        self.took_damage_this_turn = True

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def is_statused(self) -> bool:
        return self.status != Status.NONE

    def effective_speed(self) -> int:
        """Raw speed before ability/item modifications."""
        return self.base_stats["speed"]

    def has_type(self, t: str) -> bool:
        return t in self.types


# ---------------------------------------------------------------------------
# Side  (one per player)
# ---------------------------------------------------------------------------

@dataclass
class Side:
    toxic_spikes:    int = 0   # layers (0–2)
    spikes:          int = 0   # layers (0–3)
    stealth_rock:    bool = False
    sticky_web:      bool = False
    reflect_turns:   int = 0
    light_screen_turns: int = 0
    aurora_veil_turns: int = 0
    tailwind_turns:  int = 0
    safeguard_turns: int = 0
    mist_turns:      int = 0
    party:           list[Pokemon] = field(default_factory=list)
    fainted_count:   int = 0   # Supreme Overlord

    def clear_screens(self):
        self.reflect_turns = 0
        self.light_screen_turns = 0
        self.aurora_veil_turns = 0


# ---------------------------------------------------------------------------
# BattleState
# ---------------------------------------------------------------------------

@dataclass
class BattleState:
    weather:         str = "none"
    terrain:         str = "none"
    weather_turns:   int = 0
    terrain_turns:   int = 0
    turn_number:     int = 1
    is_doubles:      bool = False

    # Field ability flags (set by PassiveFieldHook)
    weather_suppressed:     bool = False
    dark_aura_active:       bool = False
    fairy_aura_active:      bool = False
    aura_break_active:      bool = False
    neutralizing_gas_active: bool = False
    unnerve_active:         bool = False
    damp_active:            bool = False
    beads_of_ruin_active:   bool = False
    sword_of_ruin_active:   bool = False
    tablets_of_ruin_active: bool = False
    vessel_of_ruin_active:  bool = False

    def effective_weather(self) -> str:
        return "none" if self.weather_suppressed else self.weather

    def is_raining(self) -> bool:
        w = self.effective_weather()
        return w in ("rain", "heavy_rain")

    def is_sunny(self) -> bool:
        w = self.effective_weather()
        return w in ("sun", "harsh_sun")

    def is_sandstorm(self) -> bool:
        return self.effective_weather() == "sandstorm"

    def is_hail_or_snow(self) -> bool:
        return self.effective_weather() in ("hail", "snow")