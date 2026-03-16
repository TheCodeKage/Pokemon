import json
from json import JSONDecodeError

import requests
import atexit


def clean_request(url, name, session):
    response = session.get(url + f"{name.strip().replace(' ', '-')}")
    if response.text == "Not Found":
        raise ValueError("Value not found")
    response = response.json()
    return response

def load_cache(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except JSONDecodeError:
        return {}

def save_cache(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class PokeAPIClient:
    def __init__(self):
        self.session = requests.Session()
        self._url = "https://pokeapi.co/api/v2/"
        self._pokemon_cache = load_cache("../cache/pokemon.json")
        self._ability_cache = load_cache("../cache/abilities.json")
        self._move_cache = load_cache("../cache/moves.json")
        self._request_counter = 0

        atexit.register(self._save_all)

    def _save_all(self):
        save_cache("../cache/pokemon.json", self._pokemon_cache)
        save_cache("../cache/abilities.json", self._ability_cache)
        save_cache("../cache/moves.json", self._move_cache)

    def _register_request(self):
        self._request_counter += 1

        if self._request_counter >= 10:
            self._save_all()
            self._request_counter = 0

    def get_pokemon(self, name: str):
        if name not in self._pokemon_cache:
            self._pokemon_cache[name] = clean_request(self._url + 'pokemon/', name, self.session)
            self._register_request()
        response = self._pokemon_cache[name]

        stats = dict()
        for i in range(6):
            stats[response["stats"][i]["stat"]["name"]] = response["stats"][i]["base_stat"]

        types = []
        for i in range(len(response["types"])):
            types.append(response["types"][i]["type"]["name"])

        moves = []
        for i in range(len(response["moves"])):
            moves.append(response["moves"][i]["move"]["name"])

        abilities = []
        for i in response["abilities"]:
            abilities.append(i["ability"]["name"])

        return stats, types, moves, abilities

    def get_ability(self, name: str):
        if name not in self._ability_cache:
            self._ability_cache[name] = clean_request(self._url + 'ability/', name, self.session)
            self._register_request()
        response = self._ability_cache[name]
        for i in response["effect_entries"]:
            if i["language"]["name"] == "en":
                return i["short_effect"]
        return None

    def get_move(self, name: str):
        if name not in self._move_cache:
            self._move_cache[name] = clean_request(self._url + 'move/', name, self.session)
            self._register_request()
        response = self._move_cache[name]

        accuracy = response["accuracy"]
        damage_class = response["damage_class"]["name"]
        power = response["power"]
        pp = response["pp"]
        type = response["type"]["name"]
        effect_chance = response["effect_chance"]
        effect_entry = []
        priority = response["priority"]
        for i in response["effect_entries"]:
            if i["language"]["name"] == "en":
                effect_entry = i["short_effect"]
                break

        response = {
            "accuracy": accuracy,
            "damage_class": damage_class,
            "power": power,
            "pp": pp,
            "type": type,
            "effect_chance": effect_chance,
            "effect_entry": effect_entry,
            "priority": priority
        }

        return response


if __name__ == "__main__":
    client = PokeAPIClient()
    for i in range(1, 41):
        print(len(client.get_move(str(i))['effect_entry']))
