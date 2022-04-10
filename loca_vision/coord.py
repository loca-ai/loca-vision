#!/usr/bin/env python3
"""A geographical coordinate. We assume the coordinates are all in a standard
Earth reference point for now, and don't sweat the fine details too much."""

from __future__ import annotations


class Coord:
    """A geographical point on the face of the Earth."""

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    def __repr__(self):
        return f"Coord({self.lat}, {self.lon})"

    def __str__(self):
        return f"({self.lat:.5f}, {self.lon:.5f})"

    @classmethod
    def from_json(cls, json: dict) -> Coord:
        return cls(json["lat"], json["lon"])

    def to_json(self) -> dict:
        return {"lat": self.lat, "lon": self.lon}
