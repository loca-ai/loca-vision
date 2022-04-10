#!/usr/bin/env python3

from __future__ import annotations
from typing import MutableSequence
from .coord import Coord


class WikiMonument:
    """A monument populated from a Wikipedia entry."""

    def __init__(
        self, name: str, desc: str, coord: Coord, image_urls: MutableSequence[str]
    ):
        """Initializes a monument with the data."""
        self.name = name
        self.desc = desc
        self.coord = coord
        self.image_urls = image_urls

    def __repr__(self):
        return f"""WikiMonument(
            {self.name},
            {self.desc},
            {self.coord},
            {self.image_urls}
        )"""

    @classmethod
    def from_json(cls, json: dict) -> WikiMonument:
        return cls(
            json["name"],
            json["desc"],
            Coord.from_json(json["coord"]),
            json["image_urls"],
        )

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "desc": self.desc,
            "coord": self.coord.to_json(),
            "image_urls": self.image_urls,
        }
