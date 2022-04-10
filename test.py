#!/usr/bin/env python3

from loca_vision.wiki_parser import search_monuments_nearby, geosearch_pages
from loca_vision.coord import Coord
from loca_vision.gcloud import *
from loca_vision.wiki_monument import WikiMonument
import numpy as np
from tqdm import tqdm
import json


def search_area():

    objs = []
    for lat in tqdm(np.linspace(41.27, 41.34, 10)):
        for lon in np.linspace(-73, -72.8, 10):
            coord = Coord(lat, lon)
            for monument in search_monuments_nearby(coord, 1500, 10):
                obj = {
                    "name": monument.name,
                    "desc": monument.desc,
                    "coord": {"lat": monument.coord.lat, "lon": monument.coord.lon,},
                    "image_urls": monument.image_urls,
                }
                if obj not in objs:
                    objs.append(obj)

    print(len(objs), "monuments")
    with open("monuments.json", "w") as outfile:
        json.dump(objs, outfile, indent=2)


def upload_google(infile: str, outfile: str):
    with open(infile, "r") as mons_file:
        mons = json.load(mons_file)

    mons = [WikiMonument.from_json(mon) for mon in mons]

    upload_images_from_monuments(mons)
    with open(outfile, "w") as out:
        json.dump([mon.to_json() for mon in mons], out, indent=2)


# upload_google('monuments.json', 'monuments-google.json')
# upload_google("monuments-google.json", "monuments-google.json")


def test_csv():
    with open("monuments-google.json", "r") as mons_file:
        mons = json.load(mons_file)

    mons = [WikiMonument.from_json(mon) for mon in mons]
    print(monuments_to_csv(mons))


def upload_monuments():
    with open("monuments-google.json", "r") as mons_file:
        mons = json.load(mons_file)

    mons = [WikiMonument.from_json(mon) for mon in mons]
    upload_product_set(mons)


# upload_monuments()

get_similar_products_file(
    "loca-346705",
    "us-east1",
    "monuments",
    "general-v1",
    "tests/lipstick4geo.jpg",
    None,
    3,
)
