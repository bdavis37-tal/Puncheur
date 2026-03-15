"""GPX file parser — converts GPX route files into RideProfile objects.

Uses gpxpy to parse GPX files and extract the route track, which can
then be used with tagged segments for ride analysis.
"""

from __future__ import annotations

from pathlib import Path

from puncheur.models.ride_profile import RideProfile


def parse_gpx(file_path: str, route_name: str = "") -> RideProfile:
    """Parse a GPX file and return a RideProfile.

    Extracts the track from the GPX file for route visualization and
    segment matching. Segments must be tagged separately.

    Args:
        file_path: Path to the GPX file.
        route_name: Name for the ride profile.

    Returns:
        A RideProfile with the GPX file reference.

    Raises:
        FileNotFoundError: If the GPX file doesn't exist.
        ValueError: If the GPX file can't be parsed.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"GPX file not found: {file_path}")

    try:
        import gpxpy
    except ImportError:
        raise ImportError(
            "gpxpy is required for GPX file parsing. "
            "Install it with: pip install gpxpy"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
    except Exception as e:
        raise ValueError(f"Failed to parse GPX file '{file_path}': {e}")

    name = route_name or gpx.name or path.stem

    return RideProfile(
        name=name,
        gpx_file=str(path),
    )


def get_gpx_track_points(file_path: str) -> list[tuple[float, float, float | None]]:
    """Extract track points from a GPX file as (lat, lon, elevation) tuples.

    Args:
        file_path: Path to the GPX file.

    Returns:
        List of (latitude, longitude, elevation) tuples.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"GPX file not found: {file_path}")

    import gpxpy

    with open(path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude, point.elevation))

    return points
