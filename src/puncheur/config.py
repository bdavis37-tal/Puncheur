"""Configuration management for Puncheur.

Handles rider profiles, app configuration, and data directory paths.
All persistent data lives in ~/.puncheur/ as JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".puncheur"
RIDER_PROFILE_FILE = "rider_profile.json"
RIDE_PROFILES_DIR = "routes"
RIDE_HISTORY_DIR = "rides"


def get_data_dir() -> Path:
    """Return the Puncheur data directory, creating it if needed."""
    data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_routes_dir() -> Path:
    """Return the routes directory, creating it if needed."""
    routes_dir = get_data_dir() / RIDE_PROFILES_DIR
    routes_dir.mkdir(parents=True, exist_ok=True)
    return routes_dir


def get_rides_dir() -> Path:
    """Return the ride history directory, creating it if needed."""
    rides_dir = get_data_dir() / RIDE_HISTORY_DIR
    rides_dir.mkdir(parents=True, exist_ok=True)
    return rides_dir


def get_rider_profile_path() -> Path:
    """Return the path to the rider profile JSON file."""
    return get_data_dir() / RIDER_PROFILE_FILE


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file and return the parsed data."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Save data as a formatted JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def coggan_power_zones(ftp: int) -> dict[str, list[int]]:
    """Calculate Coggan's standard power zones from FTP.

    Returns a dictionary mapping zone names to [lower, upper] bounds.
    Zone 7 upper bound is capped at 9999 as a practical maximum.
    """
    return {
        "z1_recovery": [0, int(ftp * 0.55)],
        "z2_endurance": [int(ftp * 0.55) + 1, int(ftp * 0.75)],
        "z3_tempo": [int(ftp * 0.75) + 1, int(ftp * 0.90)],
        "z4_threshold": [int(ftp * 0.90) + 1, int(ftp * 1.05)],
        "z5_vo2max": [int(ftp * 1.05) + 1, int(ftp * 1.20)],
        "z6_anaerobic": [int(ftp * 1.20) + 1, int(ftp * 1.50)],
        "z7_neuromuscular": [int(ftp * 1.50) + 1, 9999],
    }
