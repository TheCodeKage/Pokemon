import enum


class StatusCondition(enum.Enum):
    PARALYSIS = "par"
    SLEEP = "slp"
    FREEZE = "frz"
    BURN = "brn"
    POISON = "psn"
    TOXIC = "tox"


class VolatileCondition(enum.Enum):
    CONFUSION = 1
    INFATUATION = 2
    TRAP = 3
    NIGHTMARE = 4
    TORMENT = 5
    DISABLE = 6
    YAWN = 7
    HEAL_BLOCK = 8
    NO_TYPE_IMMUNITY = 9
    LEECH_SEED = 10
    EMBARGO = 11
    PERISH_SONG = 12
    INGRAIN = 13
    SILENCE = 14
    TAR_SHOT = 15


class Type(enum.Enum):
    NORMAL = 1
    FIGHTING = 2
    FLYING = 3
    POISON = 4
    GROUND = 5
    ROCK = 6
    BUG = 7
    GHOST = 8
    STEEL = 9
    FIRE = 10
    WATER = 11
    GRASS = 12
    ELECTRIC = 13
    PSYCHIC = 14
    ICE = 15
    DRAGON = 16
    DARK = 17
    FAIRY = 18
    STELLAR = 19
    UNKNOWN = 10001

    @staticmethod
    def from_string(value: str):
        return Type[value.upper()]


class DamageClass(enum.Enum):
    STATUS = 0
    PHYSICAL = 1
    SPECIAL = 2


class Weather(enum.Enum):
    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SAND = "sand"
    HAIL = "hail"
