from api.request_manager import PokeAPIClient as ParentClient
from models import PokemonSpecies, Stats, Type, BaseMove, Ability


class PokeAPIClient:
    def __init__(self):
        self.client = ParentClient()

    def get_move(self, name: str):
        data = self.client.get_move(name)
        return BaseMove(name, type=Type.from_string(data['type']), power=data['power'], accuracy=data['accuracy'],
                 pp=data['pp'], damage_class=data['damage_class'], priority=data['priority'])

    def get_ability(self, name: str):
        data = self.client.get_ability(name)
        return Ability(name, data)

    def get_pokemon(self, name: str):
        data = self.client.get_pokemon(name)
        stats_data = {
            "attack": data[0]["attack"],
            "defense": data[0]["defense"],
            "speed": data[0]["speed"],
            "special_attack": data[0]["special-attack"],
            "special_defense": data[0]["special-defense"],
            "hp": data[0]["hp"]
        }
        stats = Stats(**stats_data)
        types = [Type.from_string(i) for i in data[1]]
        moves = [self.get_move(i) for i in data[2]]
        abilities = [self.get_ability(i) for i in data[3]]
        return PokemonSpecies(name, stats, types, moves, abilities)

if __name__ == "__main__":
    client = PokeAPIClient()
    print(client.get_pokemon("charmander"))
