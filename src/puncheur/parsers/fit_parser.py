"""FIT file parser — converts Garmin/Wahoo FIT files into Ride objects.

Uses the fitparse library to extract record messages containing power,
heart rate, cadence, speed, GPS position, and altitude data. GPS coordinates
in FIT files are stored as semicircles and must be converted to degrees.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from puncheur.models.ride import Ride, RidePoint

# FIT files store lat/lon in semicircles. Convert to degrees.
SEMICIRCLE_TO_DEGREES = 180.0 / (2**31)


def _semicircles_to_degrees(semicircles: int | None) -> float | None:
    """Convert FIT semicircle coordinates to decimal degrees."""
    if semicircles is None:
        return None
    return semicircles * SEMICIRCLE_TO_DEGREES


def _get_field(record: Any, field_name: str) -> Any:
    """Safely extract a field value from a FIT record message."""
    try:
        return record.get_value(field_name)
    except (KeyError, AttributeError):
        return None


def parse_fit(file_path: str) -> Ride:
    """Parse a FIT file and return a Ride object.

    Extracts all 'record' messages from the FIT file, converting each
    into a RidePoint with power, HR, cadence, speed, GPS, and altitude.

    Args:
        file_path: Path to the FIT file.

    Returns:
        A Ride object containing the parsed data points.

    Raises:
        FileNotFoundError: If the FIT file doesn't exist.
        ValueError: If the FIT file can't be parsed.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"FIT file not found: {file_path}")

    try:
        from fitparse import FitFile
    except ImportError:
        raise ImportError(
            "fitparse is required for FIT file parsing. "
            "Install it with: pip install fitparse"
        )

    try:
        fit_file = FitFile(str(path))
        fit_file.parse()
    except Exception as e:
        raise ValueError(f"Failed to parse FIT file '{file_path}': {e}")

    points: list[RidePoint] = []

    for record in fit_file.get_messages("record"):
        timestamp = _get_field(record, "timestamp")
        if timestamp is None:
            continue

        # Ensure timestamp is a datetime
        if not isinstance(timestamp, datetime):
            continue

        point = RidePoint(
            timestamp=timestamp,
            power=_get_field(record, "power"),
            heart_rate=_get_field(record, "heart_rate"),
            cadence=_get_field(record, "cadence"),
            speed=_get_field(record, "speed"),
            latitude=_semicircles_to_degrees(_get_field(record, "position_lat")),
            longitude=_semicircles_to_degrees(_get_field(record, "position_long")),
            altitude=_get_field(record, "altitude"),
        )
        points.append(point)

    # Sort by timestamp
    points.sort(key=lambda p: p.timestamp)

    ride = Ride(
        name=path.stem,
        points=points,
        source_file=str(path),
    )

    return ride
