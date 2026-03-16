from api import PokeAPIClient
from engine import BattleEngine
from models import BattlePokemon, BattleTrainer, Trainer, Pokemon, Stats

client = PokeAPIClient()
charizard = client.get_pokemon("charizard")
pikachu = client.get_pokemon("pikachu")
absol = client.get_pokemon("absol")
squirtle = client.get_pokemon("squirtle")
ninjask = client.get_pokemon("ninjask")
snorlax = client.get_pokemon("snorlax")

flamethrower = client.get_move("flamethrower")
solar_beam = client.get_move("solar-beam")
focus_blast = client.get_move("focus-blast")
roost = client.get_move("roost")

charizard_moves = [flamethrower, solar_beam, focus_blast, roost]
charizard_ability = client.get_ability("solar-power")


thunder_wave = client.get_move("thunder-wave")
volt_switch = client.get_move("volt-switch")
knock_off = client.get_move("knock-off")
protect = client.get_move("protect")

pikachu_moves = [thunder_wave, volt_switch, knock_off, protect]
pikachu_ability = client.get_ability("static")


sucker_punch = client.get_move("sucker-punch")
play_rough = client.get_move("play-rough")
pursuit = client.get_move("pursuit")

absol_moves = [knock_off, sucker_punch, play_rough, pursuit]
absol_ability = client.get_ability("justified")


water_gun = client.get_move("water-gun")
tackle = client.get_move("tackle")
bubble = client.get_move("bubble")
whirlpool = client.get_move("whirlpool")

squirtle_moves = [water_gun, tackle, bubble, whirlpool]
squirtle_ability = client.get_ability("torrent")


leech_life = client.get_move("leech-life")
u_turn = client.get_move("u-turn")
aeriel_ace = client.get_move("aerial-ace")
swords_dance = client.get_move("swords-dance")

ninjask_moves = [leech_life, u_turn, aeriel_ace, swords_dance]
ninjask_ability = client.get_ability("speed-boost")


curse = client.get_move("curse")
body_slam = client.get_move("body-slam")
rest = client.get_move("rest")
earthquake = client.get_move("earthquake")

snorlax_moves = [curse, body_slam, rest, earthquake]
snorlax_ability = client.get_ability("thick-fat")

IVs = Stats(31, 31, 31, 31, 31, 31)
EVs = Stats(35, 55, 40, 50, 50, 90)

ch1 = Pokemon(charizard, charizard_moves, IVs, EVs, charizard_ability, 100, "charla")
pi1 = Pokemon(pikachu, pikachu_moves, IVs, EVs, pikachu_ability, 100, "pika")
ab1 = Pokemon(absol, absol_moves, IVs, EVs, absol_ability, 100, "doom")
sq1 = Pokemon(squirtle, squirtle_moves, IVs, EVs, squirtle_ability, 100, "squirter")
nk1 = Pokemon(ninjask, ninjask_moves, IVs, EVs, ninjask_ability, 100, "ninja")
sl1 = Pokemon(snorlax, snorlax_moves, IVs, EVs, snorlax_ability, 100, "kuma")

ch2 = Pokemon(charizard, charizard_moves, IVs, EVs, charizard_ability, 100, "charlie")
pi2 = Pokemon(pikachu, pikachu_moves, IVs, EVs, pikachu_ability, 100, "haraami")
ab2 = Pokemon(absol, absol_moves, IVs, EVs, absol_ability, 100, "blacky")
sq2 = Pokemon(squirtle, squirtle_moves, IVs, EVs, squirtle_ability, 100, "pichkaari")
nk2 = Pokemon(ninjask, ninjask_moves, IVs, EVs, ninjask_ability, 100, "kasha")
sl2 = Pokemon(snorlax, snorlax_moves, IVs, EVs, snorlax_ability, 100, "bhaalu")

naman = Trainer("Naman", 1, [ch1, pi1, ab1, sq1, nk1, sl1])
gopal = Trainer("Gopal", 2, [ch2, pi2, ab2, sq2, nk2, sl2])

engine = BattleEngine(naman, gopal)
engine.start_battle()