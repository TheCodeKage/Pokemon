import requests


def clean_request(url, name, session):
    response = session.get(url + f"{name.strip().replace(' ', '-')}")
    if response.text == "Not Found":
        raise ValueError("Value not found")
    response = response.json()
    return response


class PokeAPIClient:
    def __init__(self):
        self.session = requests.Session()
        self._url = "https://pokeapi.co/api/v2/"

    def get_pokemon(self, name: str):
        response = clean_request(self._url + 'pokemon/', name, self.session)

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
        response = clean_request(self._url + 'ability/', name, self.session)
        for i in response["effect_entries"]:
            if i["language"]["name"] == "en":
                return i["short_effect"]
        return None

    def get_move(self, name: str):
        response = clean_request(self._url + 'move/', name, self.session)

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
