"""Ride profile model — a GPX route with tagged segments.

A RideProfile represents a known route (like "Tuesday Group Ride") with
its GPX track and a list of tagged segments marking the climbs and key
efforts along the way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from puncheur.config import get_routes_dir, load_json, save_json
from puncheur.models.segment import Segment


@dataclass
class RideProfile:
    """A saved ride route with tagged segments.

    Attributes:
        name: Route name (e.g., "Tuesday Group Ride").
        gpx_file: Path to the associated GPX file.
        segments: List of tagged segments on this route.
    """

    name: str = ""
    gpx_file: str = ""
    segments: list[Segment] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "name": self.name,
            "gpx_file": self.gpx_file,
            "segments": [s.to_dict() for s in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RideProfile:
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            gpx_file=data.get("gpx_file", ""),
            segments=[Segment.from_dict(s) for s in data.get("segments", [])],
        )

    def save(self, path: Optional[Path] = None) -> None:
        """Save ride profile to JSON file in the routes directory."""
        if path is None:
            slug = self.name.lower().replace(" ", "_")
            path = get_routes_dir() / f"{slug}.json"
        save_json(path, self.to_dict())

    @classmethod
    def load(cls, name_or_path: str) -> RideProfile:
        """Load a ride profile by name or file path.

        If name_or_path is a path to an existing file, load it directly.
        Otherwise, treat it as a route name and look in the routes directory.
        """
        path = Path(name_or_path)
        if path.exists():
            data = load_json(path)
            return cls.from_dict(data)

        # Try as a route name
        slug = name_or_path.lower().replace(" ", "_")
        route_path = get_routes_dir() / f"{slug}.json"
        if route_path.exists():
            data = load_json(route_path)
            return cls.from_dict(data)

        raise FileNotFoundError(
            f"Route '{name_or_path}' not found. "
            f"Run 'puncheur route list' to see available routes."
        )
