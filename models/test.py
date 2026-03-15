from models import *

thunderbolt = BaseMove(name="Thunderbolt", type=Type.ELECTRIC, power=90, accuracy=100, pp=15, damage_class=DamageClass.SPECIAL)
iron_tail = BaseMove(name="Iron Tail", type=Type.STEEL, power=80, accuracy=100, pp=15, damage_class=DamageClass.PHYSICAL)
electro_ball = BaseMove(name="Electro Ball", type=Type.ELECTRIC, power=100, accuracy=100, pp=10, damage_class=DamageClass.SPECIAL, effect_entry="Power is higher when the user has greater Speed than the target, up to a maximum of 150.")
volt_tackle = BaseMove(name="Volt Tackle", type=Type.ELECTRIC, power=50, accuracy=100, pp=20, damage_class=DamageClass.PHYSICAL)

moves = [thunderbolt, iron_tail, electro_ball, volt_tackle]

static = Ability("static", "paralyzes opponents on contact.")
lightning_rod = Ability("lightning rod", "Immune to electric attacks.")

abilities = [static, lightning_rod]


pikachu = PokemonSpecies(name="Pikachu", stats=Stats(35, 55, 40, 50, 50, 90), types=[Type.ELECTRIC], moves=moves, abilities=abilities)
pika = Pokemon(pikachu, moves=moves, IVs=Stats(31, 31, 31, 31, 31, 31), EVs=Stats(35, 55, 40, 50, 50, 90) ,level=100, ability=lightning_rod, current_hp=100)
battle_pika = BattlePokemon(pika)
print(battle_pika)