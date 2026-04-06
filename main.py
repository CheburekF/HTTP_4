import sys
import requests
from PIL import Image
from io import BytesIO
from map_params import get_map_params_two_points

GEOCODER_URL = "http://geocode-maps.yandex.ru/1.x/"
GEOCODER_KEY = "8013b162-6b42-4997-9691-77b7074026e0"
SEARCH_URL = "https://search-maps.yandex.ru/v1/"
SEARCH_KEY = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
STATIC_URL = "https://static-maps.yandex.ru/v1"
STATIC_KEY = "f3a0fe3a-b07e-4840-a1da-06f18b2ddf13"


def get_origin(address):
    params = {
        "apikey": GEOCODER_KEY,
        "geocode": address,
        "format": "json",
    }
    response = requests.get(GEOCODER_URL, params=params)
    if not response:
        print("Ошибка геокодера:", response.status_code, response.reason)
        sys.exit(1)
    members = response.json()["response"]["GeoObjectCollection"]["featureMember"]
    if not members:
        print("Адрес не найден.")
        sys.exit(1)
    pos = members[0]["GeoObject"]["Point"]["pos"].split()
    return float(pos[0]), float(pos[1])


def find_pharmacies(ll, count=10):
    params = {
        "apikey": SEARCH_KEY,
        "text": "аптека",
        "lang": "ru_RU",
        "ll": f"{ll[0]},{ll[1]}",
        "type": "biz",
        "results": count,
    }
    response = requests.get(SEARCH_URL, params=params)
    if not response:
        print("Ошибка поиска:", response.status_code, response.reason)
        sys.exit(1)
    features = response.json()["features"]
    if not features:
        print("Аптеки не найдены.")
        sys.exit(1)
    return features


def get_marker(pharmacy):
    hours = pharmacy["properties"]["CompanyMetaData"].get("Hours", {})
    availabilities = hours.get("Availabilities", [])

    if not availabilities:
        return "pm2grm"

    for slot in availabilities:
        if slot.get("TwentyFourHours"):
            return "pm2gng"

    return "pm2blm"


def get_marker_description(marker):
    if marker == "pm2gng":
        return "круглосуточная"
    if marker == "pm2blm":
        return "некруглосуточная"
    return "нет данных о времени"


address = " ".join(sys.argv[1:])
origin = get_origin(address)
pharmacies = find_pharmacies(origin)

pt_parts = [f"{origin[0]},{origin[1]},pm2rdm"]

print(f"Исходный адрес: {address}\n")
print(f"{'№':<3} {'Название':<35} {'Режим':<22} {'Адрес'}")
print("-" * 100)

all_lons = [origin[0]]
all_lats = [origin[1]]

for i, pharmacy in enumerate(pharmacies, 1):
    meta = pharmacy["properties"]["CompanyMetaData"]
    name = meta["name"]
    addr = meta["address"]
    coords = pharmacy["geometry"]["coordinates"]
    lon, lat = coords[0], coords[1]

    all_lons.append(lon)
    all_lats.append(lat)

    marker = get_marker(pharmacy)
    pt_parts.append(f"{lon},{lat},{marker}")

    print(f"{i:<3} {name:<35} {get_marker_description(marker):<22} {addr}")

corner1 = (min(all_lons), min(all_lats))
corner2 = (max(all_lons), max(all_lats))

map_params = get_map_params_two_points(corner1, corner2, STATIC_KEY)
map_params["pt"] = "~".join(pt_parts)

response = requests.get(STATIC_URL, params=map_params)
if not response:
    print("Ошибка StaticAPI:", response.status_code, response.reason)
    sys.exit(1)

image = Image.open(BytesIO(response.content))
image.show()
