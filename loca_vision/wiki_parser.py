#!/usr/bin/env python3

"""Takes data from Wikipedia and uses it to pre-populate monument data."""

from typing import Sequence
import requests

from .wiki_monument import WikiMonument
from .coord import Coord

BASE_URL = "https://en.wikipedia.org/w/api.php"

base_params = {"action": "query", "utf8": 1, "maxlag": 1, "format": "json"}
headers = {"User-Agent": "Loca v0.1 (https://github.com/loca-ai/loca-vision)"}


def geosearch_pages(coord: Coord, radius: float, limit=200) -> Sequence[int]:
    """Generates all pages with location no more than the given radius (in meters)
    away from the given coordinates. """
    params = {
        "list": "geosearch",
        "gscoord": f"{coord.lat}|{coord.lon}",
        "gsradius": radius,
        "gslimit": limit,
    }

    r = requests.get(BASE_URL, params={**base_params, **params}, headers=headers)
    r.raise_for_status()
    json = r.json()
    if "query" not in json:
        return []

    return [page["pageid"] for page in json["query"]["geosearch"]]


def get_monuments(pageids: Sequence[int]) -> Sequence[WikiMonument]:
    """Given a set of page IDs, returns a list of WikiMonuments objects with images, description, name, and coordinates."""
    params = {
        "prop": "images|extracts|pageimages|coordinates",
        "formatversion": 2,
        "pageids": "|".join(map(str, pageids)),
        "redirects": 1,
        "explaintext": 1,
        "exintro": 1,
    }
    r = requests.get(BASE_URL, params={**base_params, **params}, headers=headers)
    r.raise_for_status()
    monuments = []
    if "query" not in r.json():
        return []

    for page in r.json()["query"]["pages"]:
        image_titles = []
        if "pageimage" in page.keys():
            image_titles.append("File:" + page["pageimage"])

        for im in page.get("images", []):
            title = im["title"]
            if not title.endswith("svg") and title not in image_titles:
                # skip SVGs, usually icons
                image_titles.append(title)

        image_urls = get_image_urls(image_titles)
        coord = Coord(page["coordinates"][0]["lat"], page["coordinates"][0]["lon"])

        monuments.append(
            WikiMonument(page["title"], page["extract"], coord, image_urls)
        )

    return monuments


def get_image_urls(titles: Sequence[str]) -> Sequence[str]:
    """Given a list of image names from Wikipedia, gets the URLs corresponding to those images."""
    params = {
        "prop": "imageinfo",
        "titles": "|".join(titles),
        "iiprop": "url",
    }
    r = requests.get(BASE_URL, params={**base_params, **params}, headers=headers)
    r.raise_for_status()
    json = r.json()
    if "query" not in json:
        return []

    return [page["imageinfo"][0]["url"] for page in json["query"]["pages"].values()]


def search_monuments_nearby(
    coord: Coord, radius: float, limit=200
) -> Sequence[WikiMonument]:
    """Searches for nearby monuments and returns them as a list."""
    return get_monuments(geosearch_pages(coord, radius, limit))
