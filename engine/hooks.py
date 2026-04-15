from dataclasses import dataclass, field
from collections.abc import Callable


@dataclass
class Hook:
    name: str
    functions: list[Callable] = field(default_factory=list)

    def _dispatch(self, *args, **kwargs):
        for func in self.functions:
            func(*args, **kwargs)

    def _pipeline(self, value, *args, **kwargs):
        for func in self.functions:
            value = func(value, *args, **kwargs)
        return value

    def add_function(self, func: Callable):
        self.functions.append(func)

    def remove_function(self, func: Callable):
        self.functions.remove(func)


# ---------------------------------------------------------------------------
# Move execution hooks  (void — functions mutate move/pokemon flags directly)
# ---------------------------------------------------------------------------

@dataclass
class BeforeSelfMoveHook(Hook):
    """Fires before the holder executes a move.

    Handles: Adaptability, Aerilate, Analytic, Blaze, Bulletproof (outgoing
    flag), Compound Eyes, Dragon's Maw, Dragonize, Flare Boost, Galvanize,
    Gale Wings, Gorilla Tactics, Guts (attack flag), Hustle, Infiltrator,
    Iron Fist, Libero, Long Reach, Mega Launcher, Merciless, Mind's Eye,
    Mold Breaker / Teravolt / Turboblaze, Mycelium Might, Normalize,
    Overgrow, Own Tempo (outgoing), Parental Bond, Pixilate, Prankster,
    Protean, Punk Rock (outgoing), Reckless, Refrigerate, Rivalry, Scrappy,
    Serene Grace, Sharpness, Sheer Force, Stench, Strong Jaw, Swarm,
    Technician, Tinted Lens, Torrent, Tough Claws, Toxic Boost, Transistor,
    Unseen Fist, Victory Star (self)
    """
    def __call__(
        self,
        attacker_pokemon,
        defender_pokemon,
        move,
        turn_order_position: int,
        first_turn: bool = True,
    ):
        self._dispatch(attacker_pokemon, defender_pokemon, move,
                       turn_order_position, first_turn)


@dataclass
class BeforeAllyMoveHook(Hook):
    """Fires before an ally executes a move.

    Handles: Power Spot, Steely Spirit, Victory Star (ally side)
    """
    def __call__(self, ability_holder, ally_pokemon, defender_pokemon, move):
        self._dispatch(ability_holder, ally_pokemon, defender_pokemon, move)


@dataclass
class BeforeOpponentMoveHook(Hook):
    """Fires before the opponent executes any move.

    Handles: Aroma Veil (mental-targeting), Bulletproof (ball/bomb),
    Soundproof
    """
    def __call__(self, ability_holder, attacker_pokemon, move):
        self._dispatch(ability_holder, attacker_pokemon, move)


@dataclass
class BeforeOpponentPriorityMoveHook(Hook):
    """Fires before an opponent uses a move with positive priority.

    Handles: Armor Tail, Dazzling, Queenly Majesty
    """
    def __call__(self, ability_holder, attacker_pokemon, move):
        self._dispatch(ability_holder, attacker_pokemon, move)


# ---------------------------------------------------------------------------
# Damage calculation hooks  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class BeforeDamageCalcHook(Hook):
    """Fires during damage calculation before the final value is committed.
    Each registered function receives the current damage value and returns
    the modified value.

    Handles: Battle Armor / Shell Armor (prevent crit), Filter / Prism Armor /
    Solid Rock (SE × 0.75), Fluffy (contact × 0.5; Fire × 2), Fur Coat
    (physical × 0.5), Heatproof (Fire/burn × 0.5), Ice Scales (special × 0.5),
    Levitate (Ground immunity), Marvel Scale (Defense × 1.5 if statused),
    Mega Sol, Multiscale / Shadow Shield (full HP × 0.5), Neuroforce
    (SE × 1.25), Purifying Salt (Ghost × 0.5), Sniper (crit multiplier),
    Sturdy (OHKO / lethal → 1 HP), Tera Shell (full HP → NVE result),
    Thick Fat (Fire/Ice × 0.5), Wonder Guard (non-SE → 0)
    """
    def __call__(
        self,
        attacker_pokemon,
        defender_pokemon,
        move,
        damage: int,
        is_critical: bool,
        effectiveness: float,
    ) -> int:
        return self._pipeline(damage, attacker_pokemon, defender_pokemon,
                              move, is_critical, effectiveness)


@dataclass
class BeforeAllyDamageCalcHook(Hook):
    """Fires during damage calc when an ally is the target.
    Each registered function receives and returns the damage value.

    Handles: Friend Guard (ally damage × 0.75)
    """
    def __call__(
        self,
        ability_holder,
        ally_pokemon,
        attacker_pokemon,
        move,
        damage: int,
    ) -> int:
        return self._pipeline(damage, ability_holder, ally_pokemon,
                              attacker_pokemon, move)


# ---------------------------------------------------------------------------
# Stat modification hooks  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class BeforeSelfStatModifyHook(Hook):
    """Fires before a stat stage change is applied to the holder.
    Each registered function receives the current stage delta and returns
    the modified delta. Return 0 to block entirely.

    Handles: Big Pecks (Defense drops), Clear Body / Full Metal Body /
    White Smoke (all drops), Contrary (reverse direction), Hyper Cutter
    (Attack drops), Keen Eye (accuracy drops), Mirror Armor (reflect drops),
    Simple (double all changes)
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        stat: str,
        stages: int,
    ) -> int:
        return self._pipeline(stages, ability_holder, source_pokemon, stat)


@dataclass
class BeforeAllyStatModifyHook(Hook):
    """Fires before a stat stage change is applied to an ally.
    Each registered function receives and returns the stage delta.

    Handles: Flower Veil (prevent drops on Grass-type allies)
    """
    def __call__(
        self,
        ability_holder,
        ally_pokemon,
        source_pokemon,
        stat: str,
        stages: int,
    ) -> int:
        return self._pipeline(stages, ability_holder, ally_pokemon,
                              source_pokemon, stat)


@dataclass
class BeforeSelfStatCalcHook(Hook):
    """Fires when the holder's effective stat value is computed.
    Each registered function receives and returns the stat value.

    Handles: Grass Pelt (Defense in Grassy Terrain), Huge Power / Pure Power
    (Attack × 2), Minus / Plus (Sp. Atk with ally), Slow Start (Attack/Speed
    halved for 5 turns), Defeatist (Attack/Sp. Atk halved ≤50% HP)
    """
    def __call__(
        self,
        ability_holder,
        stat: str,
        raw_value: int,
        battle_state,
    ) -> int:
        return self._pipeline(raw_value, ability_holder, stat, battle_state)


# ---------------------------------------------------------------------------
# Status application hooks  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class BeforeStatusApplyHook(Hook):
    """Fires before a status condition is applied to the holder.
    Each registered function receives and returns a blocked bool.
    Return True to block the status.

    Handles: Comatose (block non-sleep), Corrosion (allow on Steel/Poison),
    Immunity (poison), Insomnia / Vital Spirit (sleep), Leaf Guard (sun),
    Limber (paralysis), Magma Armor (freeze), Oblivious (infatuation/Taunt),
    Own Tempo (confusion), Pastel Veil (poison, self+ally), Purifying Salt
    (all status), Sweet Veil (sleep, self+ally), Water Veil (burn)
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        status: str,
        battle_state,
    ) -> bool:
        return self._pipeline(False, ability_holder, source_pokemon,
                              status, battle_state)


@dataclass
class BeforeAllyStatusApplyHook(Hook):
    """Fires before a status condition is applied to an ally.
    Each registered function receives and returns a blocked bool.

    Handles: Pastel Veil (poison for allies), Sweet Veil (sleep for allies)
    """
    def __call__(
        self,
        ability_holder,
        ally_pokemon,
        source_pokemon,
        status: str,
        battle_state,
    ) -> bool:
        return self._pipeline(False, ability_holder, ally_pokemon,
                              source_pokemon, status, battle_state)


# ---------------------------------------------------------------------------
# Speed calculation hook  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class SpeedCalculationHook(Hook):
    """Fires when turn order speed is computed for the holder.
    Each registered function receives and returns the speed value.

    Handles: Chlorophyll (sun × 2), Quick Feet (statused × 1.5),
    Sand Rush (sandstorm × 2), Slush Rush (snow × 2), Surge Surfer
    (Electric Terrain × 2), Swift Swim (rain × 2), Unburden (post-item × 2)
    """
    def __call__(
        self,
        ability_holder,
        base_speed: int,
        battle_state,
    ) -> int:
        return self._pipeline(base_speed, ability_holder, battle_state)


# ---------------------------------------------------------------------------
# Accuracy / evasion hook  (pipeline — functions receive and return float)
# ---------------------------------------------------------------------------

@dataclass
class BeforeAccuracyCalcHook(Hook):
    """Fires during accuracy resolution.
    Each registered function receives and returns the accuracy value.

    Handles: Keen Eye (ignore evasion), No Guard (force 1.0), Sand Veil
    (evasion boost in sand), Snow Cloak (evasion boost in snow), Tangled Feet
    (evasion boost while confused), Wonder Skin (status moves → 50%),
    Victory Star (× 1.1)
    """
    def __call__(
        self,
        attacker_pokemon,
        defender_pokemon,
        move,
        accuracy: float,
    ) -> float:
        return self._pipeline(accuracy, attacker_pokemon, defender_pokemon, move)


# ---------------------------------------------------------------------------
# Priority / turn order hooks  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class BeforeTurnOrderCalcHook(Hook):
    """Fires before the turn order for this move is finalised.
    Each registered function receives and returns the priority value.

    Handles: Gale Wings (+1 at full HP), Prankster (+1 on status moves),
    Quick Draw (18% → move first), Stall (always last), Triage (+3 on
    restorative moves)
    """
    def __call__(
        self,
        ability_holder,
        move,
        current_priority: int,
        battle_state,
    ) -> int:
        return self._pipeline(current_priority, ability_holder, move,
                              battle_state)


@dataclass
class BeforeMoveRedirectHook(Hook):
    """Fires when the engine checks whether a move should be redirected.
    Each registered function receives and returns an ignore bool.

    Handles: Propeller Tail, Stalwart
    """
    def __call__(self, ability_holder, move) -> bool:
        return self._pipeline(False, ability_holder, move)


# ---------------------------------------------------------------------------
# Entry / exit hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnSelfEnterHook(Hook):
    """Fires when the holder switches into battle.

    Handles: Anticipation, As One (register sub-abilities), Costar,
    Curious Medicine, Dauntless Shield, Dark Aura, Delta Stream,
    Desolate Land, Download, Drizzle, Drought, Electric Surge, Embody Aspect,
    Fairy Aura, Forewarn, Grassy Surge, Hadron Engine, Illusion, Imposter,
    Intrepid Sword, Intimidate, Misty Surge, Multitype, Orichalcum Pulse,
    Pastel Veil (self cure), Primordial Sea, Psychic Surge, RKS System,
    Sand Stream, Screen Cleaner, Slow Start (begin counter), Snow Warning,
    Supersweet Syrup, Supreme Overlord, Tera Shift, Teraform Zero, Trace,
    Unnerve
    """
    def __call__(self, ability_holder, battle_state):
        self._dispatch(ability_holder, battle_state)


@dataclass
class OnAllyEnterHook(Hook):
    """Fires when an ally switches into battle.

    Handles: Hospitality
    """
    def __call__(self, ability_holder, ally_pokemon, battle_state):
        self._dispatch(ability_holder, ally_pokemon, battle_state)


@dataclass
class OnSelfSwitchOutHook(Hook):
    """Fires when the holder switches out of battle.

    Handles: Natural Cure, Regenerator, Zero to Hero
    """
    def __call__(self, ability_holder, battle_state):
        self._dispatch(ability_holder, battle_state)


# ---------------------------------------------------------------------------
# Hit taken hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnHitTakenHook(Hook):
    """Fires after the holder takes damage from any move.

    Handles: Color Change, Cotton Down, Cursed Body, Electromorphosis,
    Illusion (break disguise), Sand Spit, Seed Sower, Stamina,
    Steam Engine (Fire/Water), Thermal Exchange (Fire), Water Compaction (Water),
    Wind Power (wind moves)
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        damage_dealt: int,
        battle_state,
    ):
        self._dispatch(ability_holder, attacker_pokemon, move,
                       damage_dealt, battle_state)


@dataclass
class OnContactHitTakenHook(Hook):
    """Fires after the holder takes damage from a contact move.

    Handles: Cute Charm, Effect Spore, Flame Body, Gooey, Iron Barbs /
    Rough Skin, Lingering Aroma, Mummy, Perish Body, Pickpocket (self has
    no item, attacker does), Poison Point, Static, Tangling Hair,
    Wandering Spirit
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        damage_dealt: int,
        battle_state,
    ):
        self._dispatch(ability_holder, attacker_pokemon, move,
                       damage_dealt, battle_state)


@dataclass
class OnPhysicalHitTakenHook(Hook):
    """Fires after the holder takes damage from a physical move.

    Handles: Toxic Debris, Weak Armor
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        damage_dealt: int,
        battle_state,
    ):
        self._dispatch(ability_holder, attacker_pokemon, move,
                       damage_dealt, battle_state)


@dataclass
class OnCritHitTakenHook(Hook):
    """Fires after the holder takes a critical hit.

    Handles: Anger Point
    """
    def __call__(self, ability_holder, attacker_pokemon, move, battle_state):
        self._dispatch(ability_holder, attacker_pokemon, move, battle_state)


@dataclass
class OnDamageTakenThresholdHook(Hook):
    """Fires when the holder's HP crosses a defined threshold after damage.

    Handles: Anger Shell (≤50%), Berserk (≤50%), Emergency Exit (≤50%),
    Power Construct (≤50%), Shields Down (≤50%), Wimp Out (≤50%),
    Zen Mode (≤50%)
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        hp_ratio_before: float,
        hp_ratio_after: float,
        battle_state,
    ):
        self._dispatch(ability_holder, attacker_pokemon, move,
                       hp_ratio_before, hp_ratio_after, battle_state)


# ---------------------------------------------------------------------------
# Hit dealt hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnHitDealtHook(Hook):
    """Fires after the holder successfully deals damage.

    Handles: Magician, Poison Touch, Toxic Chain
    """
    def __call__(
        self,
        ability_holder,
        defender_pokemon,
        move,
        damage_dealt: int,
        battle_state,
    ):
        self._dispatch(ability_holder, defender_pokemon, move,
                       damage_dealt, battle_state)


# ---------------------------------------------------------------------------
# Drain / indirect damage hooks  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class OnDrainMoveAgainstSelfHook(Hook):
    """Fires when a drain move targets the holder.
    Each registered function receives and returns the drain amount.
    Return a negative value to deal damage to the attacker instead.

    Handles: Liquid Ooze
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        drain_amount: int,
    ) -> int:
        return self._pipeline(drain_amount, ability_holder, attacker_pokemon,
                              move)


@dataclass
class BeforeIndirectDamageHook(Hook):
    """Fires before any indirect damage is applied to the holder.
    Each registered function receives and returns the damage amount.
    Return 0 to nullify.

    Handles: Magic Guard (nullify all), Overcoat (weather + powder),
    Poison Heal (override poison tick → HP restore, return 0 here and
    trigger heal separately)
    """
    def __call__(
        self,
        ability_holder,
        damage_source: str,
        damage_amount: int,
        battle_state,
    ) -> int:
        return self._pipeline(damage_amount, ability_holder, damage_source,
                              battle_state)


# ---------------------------------------------------------------------------
# Faint hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnSelfFaintHook(Hook):
    """Fires immediately before the holder faints.

    Handles: Aftermath, Innards Out
    """
    def __call__(self, ability_holder, attacker_pokemon, battle_state):
        self._dispatch(ability_holder, attacker_pokemon, battle_state)


@dataclass
class OnOpponentFaintHook(Hook):
    """Fires when an opponent is knocked out.

    Handles: Battle Bond, Beast Boost, Chilling Neigh, Grim Neigh, Moxie
    """
    def __call__(self, ability_holder, fainted_pokemon, battle_state):
        self._dispatch(ability_holder, fainted_pokemon, battle_state)


@dataclass
class OnAnyPokemonFaintHook(Hook):
    """Fires when any Pokémon on either side faints.

    Handles: Soul-Heart
    """
    def __call__(self, ability_holder, fainted_pokemon, battle_state):
        self._dispatch(ability_holder, fainted_pokemon, battle_state)


@dataclass
class OnAllyFaintHook(Hook):
    """Fires when an ally faints.

    Handles: Power of Alchemy, Receiver
    """
    def __call__(self, ability_holder, fainted_ally, battle_state):
        self._dispatch(ability_holder, fainted_ally, battle_state)


# ---------------------------------------------------------------------------
# Flinch hook  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class OnSelfFlinchHook(Hook):
    """Fires when a flinch is about to be applied to the holder.
    Each registered function receives and returns a blocked bool.
    Return True to block the flinch.

    Handles: Inner Focus (block), Steadfast (Speed +1, do not block)
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        battle_state,
    ) -> bool:
        return self._pipeline(False, ability_holder, attacker_pokemon,
                              battle_state)


# ---------------------------------------------------------------------------
# Stat drop / boost reaction hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnSelfStatDropHook(Hook):
    """Fires after the holder's stat is successfully lowered by an external source.

    Handles: Competitive (Sp. Atk +2), Defiant (Attack +2)
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        stat: str,
        stages: int,
        battle_state,
    ):
        self._dispatch(ability_holder, source_pokemon, stat, stages,
                       battle_state)


@dataclass
class OnFoeStatBoostHook(Hook):
    """Fires when an opponent's stat is raised.

    Handles: Opportunist
    """
    def __call__(
        self,
        ability_holder,
        foe_pokemon,
        stat: str,
        stages: int,
        battle_state,
    ):
        self._dispatch(ability_holder, foe_pokemon, stat, stages, battle_state)


# ---------------------------------------------------------------------------
# Secondary effect hook  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class BeforeSecondaryEffectApplyHook(Hook):
    """Fires before a move's secondary effect is applied to the holder.
    Each registered function receives and returns a blocked bool.

    Handles: Shield Dust
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        effect: str,
    ) -> bool:
        return self._pipeline(False, ability_holder, attacker_pokemon,
                              move, effect)


# ---------------------------------------------------------------------------
# Item hooks  (pipeline where a value is modified, void otherwise)
# ---------------------------------------------------------------------------

@dataclass
class OnBerryConsumeHook(Hook):
    """Fires when the holder consumes a berry.

    Handles: Cheek Pouch, Cud Chew
    """
    def __call__(self, ability_holder, berry, battle_state):
        self._dispatch(ability_holder, berry, battle_state)


@dataclass
class BeforeBerryUseHook(Hook):
    """Fires before berry activation threshold is checked.
    Each registered function receives and returns the HP threshold float.

    Handles: Gluttony (lower threshold to 75%), Ripen (double effect value)
    """
    def __call__(
        self,
        ability_holder,
        berry,
        hp_threshold: float,
    ) -> float:
        return self._pipeline(hp_threshold, ability_holder, berry)


@dataclass
class BeforeItemStealHook(Hook):
    """Fires when an effect attempts to remove the holder's held item.
    Each registered function receives and returns a blocked bool.

    Handles: Sticky Hold
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        move,
    ) -> bool:
        return self._pipeline(False, ability_holder, source_pokemon, move)


@dataclass
class OnAllyItemConsumeHook(Hook):
    """Fires when an ally consumes their held item.

    Handles: Symbiosis
    """
    def __call__(
        self,
        ability_holder,
        ally_pokemon,
        consumed_item,
        battle_state,
    ):
        self._dispatch(ability_holder, ally_pokemon, consumed_item,
                       battle_state)


# ---------------------------------------------------------------------------
# Force-switch / trap hooks  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class OnForceSwitchAttemptHook(Hook):
    """Fires when an effect attempts to force the holder to switch out.
    Each registered function receives and returns a blocked bool.

    Handles: Guard Dog, Suction Cups
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        move,
    ) -> bool:
        return self._pipeline(False, ability_holder, source_pokemon, move)


@dataclass
class OnOpponentSwitchAttemptHook(Hook):
    """Fires when an opponent attempts to switch out.
    Each registered function receives and returns a blocked bool.

    Handles: Arena Trap, Magnet Pull, Shadow Tag
    """
    def __call__(
        self,
        ability_holder,
        fleeing_pokemon,
        battle_state,
    ) -> bool:
        return self._pipeline(False, ability_holder, fleeing_pokemon,
                              battle_state)


# ---------------------------------------------------------------------------
# Weather / terrain hooks  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnWeatherChangeHook(Hook):
    """Fires when the active weather changes.

    Handles: Forecast, Solar Power (begin/end tracking)
    """
    def __call__(self, ability_holder, new_weather: str, battle_state):
        self._dispatch(ability_holder, new_weather, battle_state)


@dataclass
class OnTerrainChangeHook(Hook):
    """Fires when the active terrain changes.

    Handles: Mimicry
    """
    def __call__(self, ability_holder, new_terrain: str, battle_state):
        self._dispatch(ability_holder, new_terrain, battle_state)


# ---------------------------------------------------------------------------
# End-of-turn hook  (void)
# ---------------------------------------------------------------------------

@dataclass
class EndOfTurnHook(Hook):
    """Fires at the end of each turn after all moves resolve.

    Handles: Bad Dreams, Cud Chew (re-consume), Dry Skin (weather), Harvest,
    Healer, Hunger Switch, Hydration, Ice Body, Moody, Poison Heal, Rain Dish,
    Sand Spit (if applicable), Schooling (form check), Shed Skin, Shields Down
    (form check), Slow Start (counter tick), Solar Power (HP loss), Speed Boost,
    Truant (state flip), Zen Mode (form check)
    """
    def __call__(self, ability_holder, battle_state):
        self._dispatch(ability_holder, battle_state)


# ---------------------------------------------------------------------------
# Sleep counter hook  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class SleepTurnCounterHook(Hook):
    """Fires when the holder's sleep turn counter is decremented.
    Each registered function receives the current sleep turns remaining and
    the current decrement, and returns a modified decrement.

    Handles: Early Bird
    """
    def __call__(
        self,
        ability_holder,
        current_sleep_turns: int,
        decrement: int,
    ) -> int:
        return self._pipeline(decrement, ability_holder, current_sleep_turns)


# ---------------------------------------------------------------------------
# Weight calculation hook  (pipeline — functions receive and return float)
# ---------------------------------------------------------------------------

@dataclass
class WeightCalcHook(Hook):
    """Fires when the holder's weight is needed for a move calculation.
    Each registered function receives and returns the weight value.

    Handles: Heavy Metal (× 2), Light Metal (× 0.5)
    """
    def __call__(self, ability_holder, base_weight: float) -> float:
        return self._pipeline(base_weight, ability_holder)


# ---------------------------------------------------------------------------
# Crit calculation hook  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class BeforeCritCalcHook(Hook):
    """Fires during critical hit stage resolution.
    Each registered function receives and returns the crit stage.

    Handles: Super Luck (+1 crit stage)
    """
    def __call__(
        self,
        ability_holder,
        move,
        crit_stage: int,
    ) -> int:
        return self._pipeline(crit_stage, ability_holder, move)


# ---------------------------------------------------------------------------
# Recoil hook  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class BeforeRecoilApplyHook(Hook):
    """Fires before recoil damage is applied to the holder.
    Each registered function receives and returns the recoil amount.
    Return 0 to nullify.

    Handles: Rock Head (nullify), Reckless (registered in BeforeSelfMoveHook
    to boost power; recoil itself is not modified here)
    """
    def __call__(
        self,
        ability_holder,
        move,
        recoil_amount: int,
    ) -> int:
        return self._pipeline(recoil_amount, ability_holder, move)


# ---------------------------------------------------------------------------
# PP drain hook  (pipeline — functions receive and return int)
# ---------------------------------------------------------------------------

@dataclass
class OnOpponentMoveUsedAgainstSelfHook(Hook):
    """Fires when an opponent targets the holder with a move.
    Each registered function receives and returns the PP cost.

    Handles: Pressure
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        pp_cost: int,
    ) -> int:
        return self._pipeline(pp_cost, ability_holder, attacker_pokemon, move)


# ---------------------------------------------------------------------------
# Intimidate hook  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnIntimidateReceivedHook(Hook):
    """Fires when Intimidate targets the holder.

    Handles: Guard Dog (Attack boost; also registers to OnForceSwitchAttemptHook),
    Inner Focus (block), Own Tempo (block), Rattled (Speed +1)
    """
    def __call__(self, ability_holder, intimidator, battle_state):
        self._dispatch(ability_holder, intimidator, battle_state)


# ---------------------------------------------------------------------------
# Poison application hook  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnFoePoisonApplyHook(Hook):
    """Fires when the holder successfully poisons a foe.

    Handles: Poison Puppeteer
    """
    def __call__(
        self,
        ability_holder,
        poisoned_pokemon,
        poison_type: str,
        battle_state,
    ):
        self._dispatch(ability_holder, poisoned_pokemon, poison_type,
                       battle_state)


@dataclass
class OnSelfStatusApplyHook(Hook):
    """Fires after a status condition is successfully applied to the holder.

    Handles: Synchronize (mirror status back to source)
    """
    def __call__(
        self,
        ability_holder,
        source_pokemon,
        status: str,
        battle_state,
    ):
        self._dispatch(ability_holder, source_pokemon, status, battle_state)


# ---------------------------------------------------------------------------
# Dance move hook  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnDanceMoveUsedHook(Hook):
    """Fires immediately after any Pokémon uses a dance move.

    Handles: Dancer
    """
    def __call__(
        self,
        ability_holder,
        original_user,
        move,
        battle_state,
    ):
        self._dispatch(ability_holder, original_user, move, battle_state)


# ---------------------------------------------------------------------------
# Specific move use hook  (void)
# ---------------------------------------------------------------------------

@dataclass
class OnSpecificMoveUseHook(Hook):
    """Fires when the holder uses a specific named move.

    Handles: Gulp Missile (Surf/Dive), Stance Change (attack vs King's Shield)
    """
    def __call__(self, ability_holder, move, battle_state):
        self._dispatch(ability_holder, move, battle_state)


# ---------------------------------------------------------------------------
# Ally move targeting hook  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class BeforeAllyMoveTargetSelfHook(Hook):
    """Fires when an ally's move would hit the holder.
    Each registered function receives and returns an immune bool.

    Handles: Telepathy
    """
    def __call__(
        self,
        ability_holder,
        ally_pokemon,
        move,
    ) -> bool:
        return self._pipeline(False, ability_holder, ally_pokemon, move)


# ---------------------------------------------------------------------------
# Status move immunity hook  (pipeline — functions receive and return bool)
# ---------------------------------------------------------------------------

@dataclass
class BeforeStatusMoveTargetCheckHook(Hook):
    """Fires when a status move is about to target the holder.
    Each registered function receives and returns a blocked bool.

    Handles: Good as Gold (immune to all status moves), Prankster
    Dark-type immunity (attacker-side check — registered on the attacker,
    not the defender)
    """
    def __call__(
        self,
        ability_holder,
        attacker_pokemon,
        move,
        battle_state,
    ) -> bool:
        return self._pipeline(False, ability_holder, attacker_pokemon,
                              move, battle_state)


# ---------------------------------------------------------------------------
# Passive / field-level hook  (pipeline — functions receive and return dict)
# ---------------------------------------------------------------------------

@dataclass
class PassiveFieldHook(Hook):
    """Represents a continuously-active field effect. Queried by the engine
    during relevant calculations rather than fired on a per-event basis.
    Registered at switch-in, deregistered at switch-out.
    Each registered function receives and updates a modifiers dict.

    Handles: Air Lock / Cloud Nine (suppress weather), Aura Break (invert
    aura multipliers), Beads / Sword / Tablets / Vessel of Ruin (global stat
    reduction auras), Damp (block self-destruct), Dark Aura, Fairy Aura,
    Neutralizing Gas, Unnerve
    """
    def __call__(self, battle_state) -> dict:
        return self._pipeline({}, battle_state)


# ---------------------------------------------------------------------------
# Field-only / post-battle hooks
# ---------------------------------------------------------------------------

@dataclass
class WildEncounterRateHook(Hook):
    """Modifies wild Pokémon encounter rate. Field effect only.
    Each registered function receives and returns the encounter rate.

    Handles: Illuminate (raise rate)
    """
    def __call__(self, ability_holder, base_rate: float) -> float:
        return self._pipeline(base_rate, ability_holder)


@dataclass
class WildBattleEscapeHook(Hook):
    """Fires when the player attempts to flee a wild battle.
    Each registered function receives and returns a success bool.

    Handles: Run Away
    """
    def __call__(self, ability_holder) -> bool:
        return self._pipeline(False, ability_holder)


@dataclass
class PostBattleHook(Hook):
    """Fires after the battle ends.

    Handles: Honey Gather, Pickup
    """
    def __call__(self, ability_holder, battle_result, battle_state):
        self._dispatch(ability_holder, battle_result, battle_state)